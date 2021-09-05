# Functions for building docker images
from builder.clients.docker import docker_client, docker_api_client
from builder.authentication.authenticate import authenticate_docker_client, authenticate_ecr
from builder.authentication.ssm import fetch_credentials
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
import time


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
        builder_image = "m1l0/{}:{}-py{}-{}".format(config['framework'], config['version'], config['pyversion'], config['resource'])

    return builder_image

def create_dockerfile(config, tmpl_dir, code_dir, dockerfile_path=None, has_requirements=False, save_file=False, local=False, ecr_prefix=None):
    """
    Creates a dockerfile from train job obj

    Receives a temp directory of the project to add the required files to build the dockerfile...
    """
    module_logger.info("[ImageBuilder] Creating dockerfile...")

    proj_name = config['name']
    project_dir = '/opt/model'
    working_dir = '/opt/model/jobs'

    tags = config["tags"]
    framework_labels = config["framework_labels"]

    requirements_copy_cmd = f"COPY {code_dir}/requirements.txt {project_dir}/requirements.txt"
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
        RUN python3 -m pip install --upgrade pip && \
            python3 -m pip install --no-cache-dir --requirement {}
        """
        ).format(req_path)

    env = Environment(
        loader=FileSystemLoader(tmpl_dir)
    )

    template = env.get_template("image.jinja")
    builder_image = get_build_image(config)
    # Set dockerfile from image on config object
    config["dockerfile_from_image"] = builder_image

    dockerfile_str = template.render(builder=builder_image, files=files_copy_cmd, requirements=reqs_cmd, requirements_copy_cmd=requirements_copy_cmd, entrypoint=entrypoint, tags=tags, framework_labels=framework_labels, pyversion=config["pyversion"])

    if save_file:
        dockerfile = os.path.join(dockerfile_path, "Dockerfile")
        with open(dockerfile_path, "w+") as f:
            f.write(dockerfile_str)

        return dockerfile
    else:
        return dockerfile_str

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
    """
    Creates an archive of the build context

    Note that dockerfile is passed in here as a string
    """
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

def create_archive(target_dir, tmp_code_path):
    """
    Creates and saves the archive at tmp code path
    """
    archive = os.path.join(target_dir, "myarchive.tar.gz")
    with tarfile.open(archive, mode="w:gz", debug=2) as t:
        code_dir = os.path.split(tmp_code_path)[-1]

        for x in os.listdir(tmp_code_path):
            p = os.path.join(tmp_code_path, x)
            t.add(p, arcname=os.path.join(code_dir, os.path.basename(p)))

    return archive

def retries(max_retry_count, exception_message_prefix, seconds_to_sleep=10):
    for i in range(max_retry_count):
        yield i
        time.sleep(seconds_to_sleep)
    raise Exception(
        "'{}' has reached the maximum retry count of {}".format(
            exception_message_prefix, max_retry_count
        )
    )

def service_login(service, tag=None):
    api_client = docker_api_client()

    if service == "dockerhub":
        auth_config = fetch_credentials("dockerhub")
        registry = "https://index.docker.io/v1/"
        if len(auth_config) > 0:
            status = authenticate_docker_client(api_client, registry, auth_config)
            return status, auth_config
    elif service == "ecr":
        auth_config = fetch_credentials("ecr")
        if len(auth_config) > 0:
            ecr_url, auth_config = authenticate_ecr(auth_config, tag)
            status = authenticate_docker_client(api_client, ecr_url, auth_config)
            return status, ecr_url, auth_config


def build_docker_image(tar_archive, tag, labels, config, encoding="utf-8"):
    """
    Builds docker image with given build context in tar archive

    Note: we may need to authenticate with both ecr and dockerhub as private
    images may be used inside FROM of dockerfile if user specifies baseimage
    """
    module_logger.info("Building project with tag {}".format(tag))

    if "dkr.ecr" in config.get("dockerfile_from_image"):
        _, _, auth_config = service_login("ecr", tag)
    else:
        _, auth_config = service_login("dockerhub")

    # Using the low level api so we can stream the build...
    api_client = docker_api_client()

    # try pulling image first with auth
    target_repo, target_tag = config.get("dockerfile_from_image").split(":")
    api_client.pull(
        target_repo,
        tag=target_tag,
        auth_config=auth_config
    )

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
        'pull': False
    } 

    try:
        logs = api_client.build(**args)
        for log in logs:
            res = process_build_log(log)
            if 'Error' in res:
                raise APIError(res)
            else:
                module_logger.info(res)
                yield res

        yield "imagename: {}".format(tag)
    except ImageNotFound as e:
        module_logger.error("Error with building image: {}".format(e))
    except APIError as e:
        module_logger.error("Docker API returns an error: {}".format(e))

def push_docker_image(service, repository, revision):
    """
    Pushes built image

    Note the repository must be created first

    For ecr, we push using a url type syntax ....

    Inputs:
    service => One of "docker" or "ecr" 
    respository => Repository URL e.g. "myproject"
    revision => Repository tag e.g. "latest"
    """
    api_client = docker_api_client()

    try:
        if not repository:
            raise RuntimeError("Repository must be specified")

        if service == "dockerhub":
            status, auth_config = service_login("dockerhub")
            if status != "Login Succeeded":
                raise RuntimeError("Unable to login to Dockerhub service. Push failed.")

            repo_name = repository
        elif service == "ecr":
            # NOTE: ECR requires reauth hence logging in again...
            status, ecr_url, auth_config = service_login("ecr")
            if status != "Login Succeeded":
                raise RuntimeError("Unable to login to ECR service. Push failed.")

            repo_name = '{}/{}'.format(ecr_url.replace('https://', ''), repository)

            module_logger.info("Tagging repo {} with {} ...".format(repo_name, revision))

            image = "{}:{}".format(repository, revision)
            api_client.tag(image, repo_name, revision)

        module_logger.info("Pushing to remote repo: {}:{} ...".format(repo_name, revision))

        logs = api_client.push(repo_name, auth_config=auth_config, tag=revision, stream=True, decode=True)

        for log in logs:
            res = process_build_log(log)
            if 'Error' in res:
                raise APIError(res)
            else:
                module_logger.info(res)
                yield res

        full_repo_name = "{}:{}".format(repo_name, revision)

        yield "repository: {}".format(full_repo_name)
    except ImageNotFound as e:
        module_logger.error("Error with pushing image: {}".format(e))
    except APIError as e:
        module_logger.error("Docker API returns an error: {}".format(e))
    except RuntimeError as e:
        module_logger.error("Error with pushing image: {}".format(e))

def remove_image(repository):
    """
    Deletes the given image repo locally
    """
    api_client = docker_api_client()

    try:
        api_client.remove_image(repository, force=True)
        if "ecr" in repository:
            # need to remove the base part of the image
            # as ecr creates two images
            rsp = repository.split("/")
            api_client.remove_image("/".join(rsp[1:]), force=True)
    except ImageNotFound as e:
        module_logger.error("Error with removing image: {}".format(e))
    except APIError as e:
        module_logger.error("Docker API returns an error: {}".format(e))
    except RuntimeError as e:
        module_logger.error("Error with removing image: {}".format(e))