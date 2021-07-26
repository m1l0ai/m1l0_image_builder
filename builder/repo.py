# Functions for building docker images
from .clients import docker_client, docker_api_client
from .authenticate import authenticate_docker_client, authenticate_ecr
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


def get_build_image(config):
    """
    Generates the FROM builder string in Dockerfile

    if base image supplied it would be like 'tensorflow/0.2.4:latest' for example...
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

def build_docker_image(tar_archive, tag, labels, encoding="utf-8"):
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
        'decode': True,
        'pull': True
    } 

    try:
        logs = api_client.build(**args)
        for log in logs:
            res = process_build_log(log)
            if 'Error' in res:
                raise APIError(res)
            else:
                module_logger.info(res)

        return tag
    except ImageNotFound as e:
        module_logger.error("Error with building image: {}".format(e))
    except APIError as e:
        module_logger.error("Docker API returns an error: {}".format(e))


def push_docker_image(image, service, auth_config, repository=None):
    """
    Pushes built image

    Note for dockerhub the repository must be create first and passed in here

    For ecr, we can push using a url type syntax ....

    Inputs:
    image => "cheeproject/mnist:1"
    service => One of "docker" or "ecr" 
    auth_config => dict of username, password
    respository => Needed for dockerhub
    """

    if service == "dockerhub":
        if not repository:
            raise RuntimeError("Repository must be specified for dockerhub")

        api_client = docker_api_client()
        registry = "https://index.docker.io/v1/"
        status = authenticate_docker_client(api_client, registry, auth_config)
        if status != "Login Succeeded":
            raise RuntimeError("Unable to login to dockerhub service. Push failed.")

        tag = image.split(":")[-1]
        repo_name = "{}/{}".format(auth_config["username"], repository)
            
    elif service == "ecr":
        api_client = docker_api_client()
        ecr_url, auth_config = authenticate_ecr(auth_config, image)
        status = authenticate_docker_client(api_client, ecr_url, auth_config)
        if status != "Login Succeeded":
            raise RuntimeError("Unable to login to docker using ECR credentials. Push failed.")
        repo_name, tag = image.split(":")
        repo_name = '{}/{}'.format(ecr_url.replace('https://', ''), repo_name)

    try:
        module_logger.info("Tagging repo {} with {} ...".format(repo_name, tag))
        api_client.tag(image, repo_name, tag)

        module_logger.info("Pushing to remote repo: {}:{} ...".format(repo_name, tag))

        logs = api_client.push(repo_name, auth_config=auth_config, tag=tag, stream=True, decode=True)
        
        for log in logs:
            res = process_build_log(log)
            if 'Error' in res:
                raise APIError(res)
            else:
                module_logger.info(res)

        full_repo_name = "{}:{}".format(repo_name, tag)
        return full_repo_name
    except ImageNotFound as e:
        module_logger.error("Error with pushing image: {}".format(e))
    except APIError as e:
        module_logger.error("Docker API returns an error: {}".format(e))
    except RuntimeError as e:
        module_logger.error("Error with pushing image: {}".format(e))
