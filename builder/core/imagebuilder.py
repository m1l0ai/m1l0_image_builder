# Core classes for building images
from .repo import create_dockerfile, prepare_archive, build_docker_image, push_docker_image, remove_image
from github import Github
import tempfile
import os
import shutil
from urllib.parse import urlparse
import pkg_resources
from pathlib import Path
import traceback


class ImageBuilder:
    """
    Actual image builder class
    """
    def __init__(self, request, code_copy_path=None):
        self.request = request
        self.code_copy_path = code_copy_path
        self.code_path = request.id

    @property
    def imagename(self):
        return self._imagename

    @property
    def repository(self):
        return self._repository
    
    def build(self):
        self.config = {
            "id": self.request.id,
            "namespace": self.request.config.namespace,
            "name": self.request.config.name,
            "framework": self.request.config.framework,
            "version": self.request.config.version,
            "pyversion": self.request.config.pyversion,
            "resource": self.request.config.resource,
            "entry": self.request.config.entry,
            "revision": self.request.config.revision,
            "service": self.request.config.service,
            "repository": self.request.config.repository,
            "dockerfile": self.request.config.dockerfile
        }

        framework_labels = {}
        framework_labels["m1l0.namespace"] = self.request.config.namespace
        framework_labels["m1l0.name"] = self.request.config.name

        labels = {}
        if self.request.tags:
            for tag in self.request.tags:
                labels[tag.name] = tag.value

        self.config["tags"] = labels
        self.config["framework_labels"] = framework_labels

        has_requirements = False
        files_list = os.listdir(self.code_copy_path)
        if "requirements.txt" in files_list:
            has_requirements = True


        tmpl_dir = os.path.join(Path(__file__).resolve().cwd(), "builder", "templates")

        custom_dockerfile = False

        if len(self.config["dockerfile"]) > 0:
            custom_dockerfile = True
            df = os.path.join(self.code_copy_path, self.config["dockerfile"])
            if os.path.exists(df):
                with open(df, "r") as f:
                    dockerfile = f.read()
            else:
                raise RuntimeError("Custom dockerfile specified but not found.")
        else:
            dockerfile = create_dockerfile(self.config, tmpl_dir, self.code_path, dockerfile_path=None, has_requirements=has_requirements, save_file=False)

        build_context = prepare_archive(dockerfile, self.code_copy_path, custom_dockerfile=custom_dockerfile)

        tag = "{}:{}".format(self.config.get("repository"), self.config.get("revision"))

        for log in build_docker_image(build_context, tag, labels, self.config, self.code_copy_path, custom_dockerfile=custom_dockerfile):
            if "imagename:" in log:
                self._imagename = log
                continue
            else:
                yield log

    def push(self):
        self.config = {
            "id": self.request.id,
            "namespace": self.request.config.namespace,
            "name": self.request.config.name,
            "framework": self.request.config.framework,
            "version": self.request.config.version,
            "pyversion": self.request.config.pyversion,
            "resource": self.request.config.resource,
            "entry": self.request.config.entry,
            "revision": self.request.config.revision,
            "service": self.request.config.service,
            "repository": self.request.config.repository,
            "dockerfile": self.request.config.dockerfile
        }

        for log in push_docker_image(self.config.get("service"), self.config.get("repository"), self.config.get("revision"), self.config.get("id")):
            if "repository:" in log:
                self._repository = log
                continue
            else:
                yield log

    def cleanup_code_path(self):
        shutil.rmtree(self.code_copy_path)

    def cleanup_repository(self):
        # Delete created image self.repository else it will clog up disk
        if os.environ.get("MODE") != "Local":
            remove_image(self._repository.lstrip("repository: "))