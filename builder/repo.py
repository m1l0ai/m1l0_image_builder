# Functions for building docker images
from .clients import docker_client, docker_api_client
from docker.errors import APIError
from docker.errors import ImageNotFound
from jinja2 import Environment, FileSystemLoader
from jinja2 import select_autoescape
import os
import shutil
import logging
import contextlib
import tempfile
import shutil
import json
import textwrap
import tarfile
from io import BytesIO


module_logger = logging.getLogger('builder.repo')
module_logger.setLevel("INFO")

@contextlib.contextmanager
def tempdir(suffix="", prefix="tmp"):
    """Creates a temp dir to hold the model files"""
    tmp = tempfile.mkdtemp(suffix=suffix, prefix=prefix, dir=None)
    yield tmp
    shutil.rmtree(tmp)


def create_data_container(name, job_id, tar_archive, network='m1l0net'):
    """
    Creates a data container to store the training data
    in a volume which gets attached to the running container

    config => Configuration of building container
    tar_archive => TAR archive to upload into volume
    job_id => ID of enqueue job; used for creating unique container name
    """
    client = docker_client()

    # create data vol
    data_volume = client.volumes.create(
        name='datavol-{}-{}'.format(name, job_id),
        driver='local',
        labels={'m1l0.job-id': job_id}
    )

    # Create initial container to bind volume to
    data_dir = '/root/code'
    
    kwargs = {
        'name': 'datavol-attached-{}-{}'.format(name, job_id),
        'labels': {
            "m1l0.role": "builder",
            'm1l0.job-id': job_id,
            'm1l0.volumes': json.dumps([{'name': data_volume.name, 'destination': data_dir}])
        },
        # 'auto_remove': True,
        # 'detach': True,
        'volumes': {
            data_volume.name: {'bind': data_dir, 'mode': 'rw'}
        },
        'network': network
    }

    datavol_attached = client.containers.create(
        "ubuntu:18.04",
        command=None,
        **kwargs
    )

    res = upload_archive_into_container(datavol_attached, data_dir, tar_archive)
    module_logger.info("Upload {} into {} -> Status {}".format(filename, data_volume.name, res))
    
    return datavol_attached, data_volume


def upload_archive_into_container(container, path, archive):
    """
    Uploads the tar archive into the given container using
    put_archive
    """
    try:
        return container.put_archive(path, archive)
    except APIError as e:
        raise e
    except Exception as e:
        raise e


def get_build_image(config):
    """
    Generates the FROM builder string in Dockerfile
    """
    if "baseimage" in config:
        builder_image = config["baseimage"]
    else:
        builder_image = "{}/{}:{}-py{}-{}".format("m1l0", config['framework'], config['version'], config['pyversion'], config['resource'])

    return builder_image


def create_dockerfile(config, tmpl_dir, code_dir, dockerfile_path, has_requirements=False, save_file=False, local=False, ecr_prefix=None):
    """
    Creates a dockerfile from train job obj

    Receives a temp directory of the project to add the required files to build the dockerfile...
    """
    module_logger.info("[TrainJob] Creating dockerfile...")

    proj_name = config['name']
    project_dir = '/opt/model'
    working_dir = '/opt/model/jobs'

    files_copy_cmd = "COPY {} {}".format(code_dir, project_dir)

    # Set up entrypoint
    entrypoint = textwrap.dedent(
        """
        ENTRYPOINT ["python", "{}/{}"]
    """
    ).format(project_dir, config["entry"])

    reqs_cmd = ''
    if has_requirements:
        req_path = os.path.join(project_dir, "requirements.txt")
        reqs_cmd = textwrap.dedent(
            """
        RUN pip install --no-cache-dir --requirement {}
        """
        ).format(req_path)

    env = Environment(
        loader=FileSystemLoader(tmpl_dir)
    )

    template = env.get_template("image.jinja")
    
    dockerfile = os.path.join(dockerfile_path, "Dockerfile")

    builder_image = get_build_image(config)

    dockerfile_str = template.render(builder=builder_image, files=files_copy_cmd, requirements=reqs_cmd, entrypoint=entrypoint)

    if save_file:
        with open(dockerfile, "w+") as f:
            f.write(dockerfile_str)

        return dockerfile, builder_image
    else:
        return dockerfile_str, builder_image

def process_build_log(log):
    """Process docker build log line"""
    res = ''
    if 'stream' in log:
        res += log['stream']

    if 'status' in log:
        res += log['status']
        if 'id' in log:
            res += f" ---> {log['id']}"
        # {'status': 'Pushing', 'progressDetail': {'current': 58119680, 'total': 69212698}, 'progress': '[=========================================>         ]  58.12MB/69.21MB', 'id': 'ffc9b21953f4'}
        if 'progressDetail' in log and len(log['progressDetail']) > 0:
            res += f" Current: {log['progressDetail']['current']}, "
            if 'total' in log['progressDetail']:
                res += f" Total: {log['progressDetail']['total']}"
            res += f"\n{log['progress']}"
    if 'aux' in log:
        res += f"ID: {log['aux'].get('ID')}, Tag: {log['aux'].get('Tag')}, Digest: {log['aux'].get('Digest')}, Size: {log['aux'].get('Size')}"

    if 'error' in log:
        res += f"Error: {log['error']}"

    return res


def prepare_archive(dockerfile, tmp_code_path, encoding="utf-8"):
    tarstream = BytesIO()
    archive = tarfile.TarFile(fileobj=tarstream, mode="w")
    dockerfile_str = dockerfile.encode(encoding)
    dockerfile_tar_info = tarfile.TarInfo("Dockerfile")
    dockerfile_tar_info.size = len(dockerfile_str)
    archive.addfile(dockerfile_tar_info, BytesIO(dockerfile_str))

    code_dir = os.path.split(tmp_code_path)[-1]

    for x in os.listdir(tmp_code_path):
        p = os.path.join(tmp_code_path, x)
        archive.add(p, arcname=os.path.join(code_dir, os.path.basename(p)))

    tarstream.seek(0)
    return archive

def build_docker_image(tar_archive, tag, encoding="utf-8"):
    """
    Builds docker image with given build context in tar archive
    """
    module_logger.info("Building project with tag {}".format(tag))

    # Using the low level api so we can stream the build...
    api_client = docker_api_client()

    # Note: Setting pull: True here will cause the docker daemon to only pull images from dockerhub/remote repo so need to set it to false for using local images...
    # https://stackoverflow.com/questions/20481225/how-can-i-use-a-local-image-as-the-base-image-with-a-dockerfile
    args = {
        'fileobj': tar_archive.fileobj.getvalue(), 
        'custom_context': True, 
        'encoding': encoding, 
        'tag': tag, 
        'quiet': False, 
        'forcerm': True, 
        'rm': True, 
        'decode': True
    }

    try:
        logs = api_client.build(**args)
        for log in logs:
            res = process_build_log(log)
            if 'Error' in res:
                raise APIError(res)
            else:
                module_logger.info(res)
                # print(res)
    except ImageNotFound as e:
        module_logger.error("Error with building image: {}".format(e))
    except APIError as e:
        module_logger.error("Docker API returns an error: {}".format(e))
