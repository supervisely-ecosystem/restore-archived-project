import shutil, os, re
import supervisely as sly
import requests
import tarfile, zipfile
import globals as g
import time
import json
from tqdm import tqdm

from supervisely.io.json import load_json_file
from supervisely.api.module_api import ApiField
from supervisely.io.fs import dir_empty, get_subdirs, file_exists, archive_directory


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


def unzip_archive(archive_path, extract_path):
    sly.logger.info("Extracting files, please wait ...")
    try:
        shutil.unpack_archive(archive_path, extract_path)
    except shutil.ReadError:
        with zipfile.ZipFile(archive_path, "r") as zip_ref:
            zip_ref.extractall(extract_path)
    except Exception as e:
        raise_exception_with_troubleshooting_link(e)
    os.remove(archive_path)
    tar_parts = get_tar_parts(extract_path)
    if tar_parts:
        full_archive = combine_parts(tar_parts, extract_path)
        with tarfile.open(full_archive, "r") as tar:
            tar.extractall(extract_path)
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


def make_true_source_path(source_path, unzip_files_path, reverse_mapping):
    relative_path = (
        source_path[len(unzip_files_path) + 1 :]
        if source_path.startswith(unzip_files_path)
        else source_path
    )
    base_name, ext = os.path.splitext(relative_path)

    if base_name in reverse_mapping:
        new_name = reverse_mapping[base_name]
        new_path = os.path.join(unzip_files_path, new_name + ext)
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
            source_path = os.path.join(temp_files_path, hash_value)
            true_source_path = make_true_source_path(source_path, temp_files_path, reverse_mapping)
            if true_source_path is None:
                missed_hashes.append({"name": name, "source_path": source_path})
                continue
            destination_path = os.path.join(destination_folder, name)
            shutil.copy(true_source_path, destination_path)

        if len(missed_hashes) != 0:
            download_missed_hashes(missed_hashes, destination_folder, dataset_name)


def download_missed_hashes(missed_hashes, destination_folder, dataset_name):
    image_hashes = []
    image_destination_pathes = []
    for m_hash in missed_hashes:
        name = m_hash["name"]
        source_path: str = m_hash["source_path"]
        image_destination_path = os.path.join(destination_folder, name)
        image_hash = f"{source_path.split('/files/')[1]}"
        image_hashes.append(image_hash)
        image_destination_pathes.append(image_destination_path)
    try:
        g.api.image.download_paths_by_hashes(image_hashes, image_destination_pathes)
    except requests.HTTPError as e:
        content_json = json.loads(e.response.content.decode("utf-8"))
        message = content_json.get("details", {}).get("message", [])
        if "Hashes not found" == message:
            try:
                hashes = content_json.get("details", {}).get("hashes", [])
            except (json.JSONDecodeError, UnicodeDecodeError):
                raise e
            sly.logger.warning(f"Skipping files with this hashes for dataset '{dataset_name}'")
        else:
            raise e
        if len(hashes) != 0 and len(hashes) != len(image_hashes):
            for d_hash in hashes:
                index = image_hashes.index(d_hash)
                image_hashes.pop(index)
                image_destination_pathes.pop(index)
            g.api.image.download_paths_by_hashes(image_hashes, image_destination_pathes)


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
    project_class.upload(proj_path, api, g.wspace_id, project_name, True)
    shutil.rmtree(proj_path)
    sly.logger.info("✅ Project successfully restored")


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
    file_info = g.api.file.upload(g.team_id, tar_path, team_files_path)
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
