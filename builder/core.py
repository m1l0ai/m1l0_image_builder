# Core classes for building images
from authentication.vaultclient import fetch_credentials, unseal_vault
from repo import create_dockerfile, prepare_archive, build_docker_image, push_docker_image
from github import Github
import tempfile
import os
import shutil
from urllib.parse import urlparse
import pkg_resources
from pathlib import Path
import traceback


class GetSourceFiles:
    """
    Fetches the source files and downloads them before building image
    """
    def __init__(self, request):
        self.request = request

    def call(self):
        parsed_url = urlparse(self.request.source)
        ignores = []

        if self.request.ignores:
            for ig in self.request.ignores:
                ignores.append(ig.value)

        tmp_path = os.path.join(tempfile.gettempdir(), "code")

        print("PARSED URL > ", parsed_url)
        print("TMP DIR CONTENTS > ", os.listdir(tmp_path))

        # normally this is a uuid
        code_path = self.request.id
        code_copy_path = os.path.join(tmp_path, code_path)
        # if os.path.exists(code_copy_path):
        #     shutil.rmtree(code_copy_path)

        if parsed_url.scheme == "dir":
            # Assume that the dir refers to an existing path inside the mounted volume of this container

            try:
                # Copy from parsed_url.path to temp dir to remove ignores
                shutil.move(parsed_url.path, code_copy_path + "_tmp")
                # Copy from temp back to code_copy_path
                shutil.copytree(code_copy_path + "_tmp", code_copy_path, ignore=shutil.ignore_patterns(*ignores))

                shutil.rmtree(code_copy_path + "_tmp")
            except Exception as e:
                error_msg = "Dir copy error: \n{}\n{}".format(traceback.format_exc(), str(e))
                print(error_msg)

        elif ".git" in parsed_url.path:
            # Get token
            unseal_vault()
            auth_config = fetch_credentials("github")
            # Login to github first using token
            github_client = Github(auth_config["token"])
            repo = github_client.get_repo(parsed_url.path.lstrip("/").split(".git")[0])
            cmd = "git clone {} {}".format(repo.clone_url, code_copy_path + "_tmp")
            os.system(cmd)
            
            shutil.copytree(code_copy_path + "_tmp", code_copy_path, ignore=shutil.ignore_patterns(*ignores))

        return code_copy_path

class ImageBuilder:
    """
    Actual image builder class
    """
    def __init__(self, request, code_copy_path):
        self.request = request
        self.code_copy_path = code_copy_path
        self.code_path = request.id

    def build(self):
        labels = {}
        if self.request.tags:
            for tag in self.request.tags:
                labels[tag.name] = tag.value

        has_requirements = False
        files_list = os.listdir(self.code_copy_path)
        if "requirements.txt" in files_list:
            has_requirements = True

        self.config = {
            "namespace": self.request.namespace,
            "name": self.request.name,
            "framework": self.request.framework,
            "version": self.request.version,
            "pyversion": self.request.pyversion,
            "resource": self.request.resource,
            "entry": self.request.entry,
            "tags": labels,
            "revision": self.request.revision,
            "service": self.request.service,
            "repository": self.request.repository
        }

        tmpl_dir = os.path.join(Path(__file__).resolve().cwd(), "builder", "templates")

        dockerfile = create_dockerfile(self.config, tmpl_dir, self.code_path, dockerfile_path=None, has_requirements=has_requirements, save_file=False)

        build_context = prepare_archive(dockerfile, self.code_copy_path)

        tag = "{}/{}:{}".format(self.config["namespace"], self.config["name"], self.config["revision"])

        # TODO: Both build_docker_image and push_docker_image should return stream of logs...

        for log in build_docker_image(build_context, tag, labels):
            yield log

        # return image_name, repository_name

    def push(self):
        tag = "{}/{}:{}".format(self.config.get("namespace"), self.config.get("name"), self.config.get("revision"))

        for log in push_docker_image(tag, self.config.get("service"), self.config.get("repository")):
            yield log


    def cleanup(self):
        shutil.rmtree(self.code_copy_path)