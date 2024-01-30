import shutil, os, re
import supervisely as sly
import requests
import tarfile
import globals as g
import time
import json
from tqdm import tqdm

from supervisely.io.json import load_json_file
from supervisely.api.module_api import ApiField
from supervisely.io.fs import dir_empty, get_subdirs, file_exists, archive_directory, get_file_name


def raise_exception_with_troubleshooting_link(error: Exception):
    error.args = (
        f"Something went wrong, read the <a href={g.troubleshooting_link}>Troubleshooting Instructions</a>. If this does not help, please contact us.",
    )
    raise error


def download_file_from_dropbox(shared_link: str, destination_path, type: str):
    direct_link = shared_link.replace("dl=0", "dl=1")
    sly.logger.info(f"Start downloading backuped {type} from DropBox")

    retry_attemp = 0
    timeout = 10

    total_size = None

    while True:
        try:
            with open(destination_path, "ab") as file:
                response = requests.get(
                    direct_link,
                    stream=True,
                    headers={"Range": f"bytes={file.tell()}-"},
                    timeout=timeout,
                )
                if total_size is None:
                    total_size = int(response.headers.get("content-length", 0))
                    progress_bar = tqdm(
                        desc=f"Downloading backuped {type} from DropBox",
                        total=total_size,
                        is_size=True,
                    )
                sly.logger.info("Connection established")
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        retry_attemp = 0
                        file.write(chunk)
                        progress_bar.update(len(chunk))
        except requests.exceptions.RequestException as e:
            retry_attemp += 1
            if timeout < 90:
                timeout += 10
            if retry_attemp == 9:
                raise_exception_with_troubleshooting_link(e)
            sly.logger.warning(
                f"Downloading request error, please wait ... Retrying ({retry_attemp}/8)"
            )
            if retry_attemp <= 4:
                time.sleep(5)
            elif 4 < retry_attemp < 9:
                time.sleep(10)
        except Exception as e:
            retry_attemp += 1
            if retry_attemp == 3:
                raise_exception_with_troubleshooting_link(e)
            sly.logger.warning(f"Error: {str(e)}. Retrying ({retry_attemp}/2")

        else:
            sly.logger.info(f"{type.capitalize()} downloaded successfully")
            break


def download_backup(project_info: sly.ProjectInfo):
    files_archive_url = project_info.backup_archive.get(ApiField.URL)
    annotations_archive_url = project_info.backup_archive.get(ApiField.ANN_URL)

    if files_archive_url:
        download_file_from_dropbox(files_archive_url, g.archive_files_path, "files")

    if annotations_archive_url:
        download_file_from_dropbox(annotations_archive_url, g.archive_ann_path, "annotations")


def is_tar_part(filename):
    split_tar_pattern = r".+\.(tar\.\d{3})$"
    return bool(re.match(split_tar_pattern, filename))


def get_tar_parts(directory):
    tar_parts = []
    for filename in os.listdir(directory):
        full_path = os.path.join(directory, filename)
        if os.path.isfile(full_path) and is_tar_part(filename):
            tar_parts.append(full_path)
    return tar_parts


def combine_parts(parts_paths, output_path):
    parts_paths = sorted(parts_paths)
    output_path = os.path.join(output_path, "temp_arch.tar")
    with open(output_path, "wb") as output_file:
        for part_path in parts_paths:
            with open(part_path, "rb") as part_file:
                data = part_file.read()
                output_file.write(data)
            os.remove(part_path)
    return output_path


def extract_tar_with_progress(archive_path, extract_dir):
    with tarfile.open(archive_path, "r") as tar_ref:
        if "annotations" in get_file_name(archive_path):
            message = "Extracting annotations"
        else:
            message = "Extracting files"
        total_size = sum(file_info.size for file_info in tar_ref.getmembers())
        with tqdm(total=total_size, is_size=True, desc=message) as progress_bar:
            for file_info in tar_ref.getmembers():
                tar_ref.extract(file_info, path=extract_dir)
                progress_bar.update(file_info.size)


def unzip_archive(archive_path, extract_path):
    sly.logger.info("Extracting files, please wait ...")
    try:
        extract_tar_with_progress(archive_path, extract_path)
    except Exception as e:
        raise_exception_with_troubleshooting_link(e)
    os.remove(archive_path)
    tar_parts = get_tar_parts(extract_path)
    if tar_parts:
        full_archive = combine_parts(tar_parts, extract_path)
        extract_tar_with_progress(full_archive, extract_path)
        os.remove(full_archive)


def get_file_list(temp_files_path):
    filenames = []
    for filename in os.listdir(temp_files_path):
        if os.path.isfile(os.path.join(temp_files_path, filename)):
            filenames.append(filename)
    return filenames


def create_reverse_mapping(filenames):
    reverse_mapping = {}
    for filename in filenames:
        base_name, ext = os.path.splitext(filename)
        original_name = base_name.replace("-", "/") + ext
        reverse_mapping[original_name] = filename
    return reverse_mapping


def make_real_source_path(hash_value, temp_files_path, reverse_mapping):
    if hash_value in reverse_mapping:
        new_name = reverse_mapping[hash_value]
        new_path = os.path.join(temp_files_path, new_name)
    else:
        return None
    return new_path


def copy_files_from_json_structure(
    json_data: dict, temp_files_path, reverse_mapping, base_destination
):
    datasets = json_data.get("datasets", [])

    for dataset in datasets:
        missed_hashes = []
        dataset_name = dataset.get("name")
        images = dataset.get("images", [])

        destination_folder = os.path.join(base_destination, dataset_name, "img")

        for image in images:
            hash_value = image.get("hash")
            name = image.get("name")
            real_source_path = make_real_source_path(hash_value, temp_files_path, reverse_mapping)
            if real_source_path is None:
                missed_hashes.append({"name": name, "hash": hash_value})
                continue
            destination_path = os.path.join(destination_folder, name)
            shutil.copy(real_source_path, destination_path)

        if len(missed_hashes) != 0:
            download_missed_hashes(missed_hashes, destination_folder, dataset_name)


def download_missed_hashes(missed_hashes, destination_folder, dataset_name):
    image_hashes = []
    image_destination_pathes = []
    errors = 0
    for m_hash in missed_hashes:
        name = m_hash["name"]
        image_destination_path = os.path.join(destination_folder, name)
        image_hash = m_hash["hash"]
        image_hashes.append(image_hash)
        image_destination_pathes.append(image_destination_path)
    while True:
        if errors > 4:
            sly.logger.warning(f"⚠️ Skipping retries for dataset '{dataset_name}'")
            break
        try:
            g.api.image.download_paths_by_hashes(image_hashes, image_destination_pathes)
            break
        except requests.HTTPError as e:
            errors += 1
            content_json = json.loads(e.response.content.decode("utf-8"))
            message = content_json.get("details", {}).get("message", [])
            if "Hashes not found" == message:
                try:
                    hashes = content_json.get("details", {}).get("hashes", [])
                except (json.JSONDecodeError, UnicodeDecodeError):
                    raise e
                sly.logger.warning(f"Skipping files with this hashes for dataset '{dataset_name}'")
                if len(hashes) != 0:
                    idxs_to_remove = [
                        index for index, d_hash in enumerate(image_hashes) if d_hash in hashes
                    ]
                    for index in sorted(idxs_to_remove, reverse=True):
                        image_hashes.pop(index)
                        image_destination_pathes.pop(index)


def move_files_to_project_dir(temp_files_path, proj_path):
    for item in os.listdir(temp_files_path):
        item_path = os.path.join(temp_files_path, item)
        destination_path = os.path.join(proj_path, item)

        if os.path.isdir(item_path):
            shutil.move(item_path, destination_path)
        else:
            shutil.move(item_path, proj_path)
    shutil.rmtree(temp_files_path)


def del_files(temp_files_path, hash_name_map_path):
    shutil.rmtree(temp_files_path)
    os.remove(hash_name_map_path)


def import_project_by_type(api: sly.Api, proj_path):
    project_name = os.path.basename(os.path.normpath(proj_path))
    sly.logger.info(f"Uploading project with name [{project_name}] to instance")
    project_class: sly.Project = g.project_classes[g.project_type]
    if g.project_type == sly.ProjectType.IMAGES.value:
        check_shapes_in_images_project(proj_path)
    project_class.upload(proj_path, api, g.wspace_id, project_name, True)
    shutil.rmtree(proj_path)
    sly.logger.info("✅ Project successfully restored")


def handle_broken_ann(ann_path, meta, keep_classes):
    ann_name = os.path.basename(ann_path)
    ann_json = sly.json.load_json_file(ann_path)
    img_size = ann_json.get("size")  # {"height": 800, "width": 1067}
    if img_size is None:
        raise RuntimeError(f"Image size is not found in annotation: {ann_name}")
    img_size = img_size["height"], img_size["width"]
    description = ann_json.get("description", "")
    objects = ann_json.get("objects", [])
    tags = ann_json.get("tags", [])

    keep_labels = []
    for obj in objects:
        obj_class_name = obj.get("classTitle")
        if obj_class_name in keep_classes:
            try:
                label = sly.Label.from_json(obj, meta)
                keep_labels.append(label)
            except Exception as e:
                sly.logger.warn(f"Skipping invalid object: {repr(e)}", extra={"ann_name": ann_name})

    kepp_tags = []
    for tag in tags:
        try:
            tag = sly.Tag.from_json(tag, meta.tag_metas)
            kepp_tags.append(tag)
        except Exception as e:
            # * log error level to see what is wrong with annotation tags
            sly.logger.error(
                f"Skipping invalid tag: {repr(e)}", extra={"ann_name": ann_name}, exc_info=True
            )

    ann = sly.Annotation(
        img_size=img_size, labels=keep_labels, img_tags=kepp_tags, img_description=description
    )
    return ann


def check_shapes_in_images_project(project_dir):
    project_fs = sly.Project(project_dir, sly.OpenMode.READ)
    keep_classes = []  # will be used to filter annotations
    remove_classes = []  # will be used to remove classes from meta
    for obj_cls in project_fs.meta.obj_classes:
        if obj_cls.geometry_type != sly.Cuboid:
            keep_classes.append(obj_cls.name)
        else:
            sly.logger.warn(
                f"Class {obj_cls.name} has unsupported geometry type {obj_cls.geometry_type.name()}. "
                f"Class will be removed from meta and all annotations."
            )
            remove_classes.append(obj_cls.name)

    meta = project_fs.meta.delete_obj_classes(remove_classes)
    for dataset_fs in project_fs.datasets:
        dataset_fs: sly.Dataset
        for item_name in dataset_fs:
            ann_path = dataset_fs.get_ann_path(item_name)

            try:
                ann = sly.Annotation.load_json_file(ann_path, project_fs.meta)
                ann = ann.filter_labels_by_classes(keep_classes)
            except Exception as e:
                try:
                    ann = handle_broken_ann(ann_path, project_fs.meta, keep_classes)
                except Exception as e:
                    sly.logger.error(
                        f"Annotation file is broken. {repr(e)}. Skipping it.",
                        extra={"ann_path": ann_path},
                        exc_info=True,
                    )
                    continue
            sly.json.dump_json_file(ann.to_json(), ann_path)
    project_fs.set_meta(meta)


def prepare_image_files():
    hash_name_map = load_json_file(g.hash_name_map_path)
    filenames = get_file_list(g.temp_files_path)
    reverse_map = create_reverse_mapping(filenames)
    copy_files_from_json_structure(hash_name_map, g.temp_files_path, reverse_map, g.proj_path)
    del_files(g.temp_files_path, g.hash_name_map_path)


def prepare_download_link():
    tar_path = g.proj_path + ".tar"
    archive_directory(g.proj_path, tar_path)
    shutil.rmtree(g.proj_path)
    team_files_path = os.path.join(
        f"tmp/supervisely/export/restore-archived-project/", str(g.task_id) + "_" + tar_path
    )
    upload_progress = []

    def _print_progress(monitor, upload_progress):
        if len(upload_progress) == 0:
            upload_progress.append(
                sly.Progress(
                    message=f"Uploading {tar_path}",
                    total_cnt=monitor.len,
                    ext_logger=sly.logger,
                    is_size=True,
                )
            )
        upload_progress[0].set_current_value(monitor.bytes_read)

    file_info = g.api.file.upload(
        g.team_id,
        tar_path,
        team_files_path,
        lambda m: _print_progress(m, upload_progress),
    )
    os.remove(tar_path)
    g.api.task.set_output_archive(g.task_id, file_info.id, tar_path)


def main():
    download_backup(g.project_info)
    unzip_archive(g.archive_files_path, g.temp_files_path)
    if g.project_type == sly.ProjectType.IMAGES.value:
        if file_exists(g.archive_ann_path):
            unzip_archive(g.archive_ann_path, g.proj_path)
            prepare_image_files()
        else:
            sly.logger.debug("Attempting to restore images project with an old archive format")
            ds_dirs = get_subdirs(g.temp_files_path)
            for ds_dir in ds_dirs:
                if dir_empty(os.path.join(g.temp_files_path, ds_dir, "ann")):
                    raise FileNotFoundError(
                        f"No annotation files were found in dataset '{ds_dir}' when trying to restore images project with an old archive format"
                    )
            move_files_to_project_dir(g.temp_files_path, g.proj_path)
    else:
        move_files_to_project_dir(g.temp_files_path, g.proj_path)

    if g.download_mode:
        prepare_download_link()
    else:
        import_project_by_type(g.api, g.proj_path)


if __name__ == "__main__":
    sly.main_wrapper("main", main)
