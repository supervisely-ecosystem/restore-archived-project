import os
import supervisely as sly

from dotenv import load_dotenv
from supervisely.io.fs import mkdir

if sly.is_development():
    load_dotenv("local.env")
    load_dotenv(os.path.expanduser("~/supervisely.env"))


api = sly.Api.from_env()

project_id = int(os.environ.get("modal.state.slyProjectId"))
task_id = int(os.environ.get("TASK_ID"))
project_info: sly.ProjectInfo = api.project.get_info_by_id(project_id)
project_type = project_info.type
wspace_id = project_info.workspace_id
proj_path = os.path.join("./", str(project_id) + "_" + project_info.name)
mkdir(proj_path)


temp_files_path = os.path.join(proj_path, "files")
hash_name_map_path = os.path.join(proj_path, "hash_name_map.json")
archive_files_path = os.path.join(proj_path, "files.tar")
archive_ann_path = os.path.join(proj_path, "annotations.tar")

project_classes = {
    "images": sly.Project,
    "videos": sly.VideoProject,
    "volumes": sly.VolumeProject,
    "point_clouds": sly.PointcloudProject,
    "point_cloud_episodes": sly.PointcloudEpisodeProject,
}
