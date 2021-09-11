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
    def __init__(self, request, code_copy_path):
        self.request = request
        self.code_copy_path = code_copy_path
        self.code_path = request.id

    def build(self):
        framework_labels = {}
        framework_labels["m1l0.namespace"] = self.request.namespace
        framework_labels["m1l0.name"] = self.request.name

        labels = {}
        if self.request.tags:
            for tag in self.request.tags:
                labels[tag.name] = tag.value

        has_requirements = False
        files_list = os.listdir(self.code_copy_path)
        if "requirements.txt" in files_list:
            has_requirements = True

        self.config = {
            "id": self.request.id,
            "namespace": self.request.namespace,
            "name": self.request.name,
            "framework": self.request.framework,
            "version": self.request.version,
            "pyversion": self.request.pyversion,
            "resource": self.request.resource,
            "entry": self.request.entry,
            "tags": labels,
            "framework_labels": framework_labels,
            "revision": self.request.revision,
            "service": self.request.service,
            "repository": self.request.repository
        }

        tmpl_dir = os.path.join(Path(__file__).resolve().cwd(), "builder", "templates")

        dockerfile = create_dockerfile(self.config, tmpl_dir, self.code_path, dockerfile_path=None, has_requirements=has_requirements, save_file=False)

        build_context = prepare_archive(dockerfile, self.code_copy_path)

        # tag = "{}/{}:{}".format(self.config["namespace"], self.config["name"], self.config["revision"])
        tag = "{}:{}".format(self.config.get("repository"), self.config.get("revision"))

        for log in build_docker_image(build_context, tag, labels, self.config):
            if "imagename:" in log:
                self.imagename = log
                continue
            else:
                yield log

    def push(self):
        for log in push_docker_image(self.config.get("service"), self.config.get("repository"), self.config.get("revision"), self.config.get("id")):
            if "repository:" in log:
                self.repository = log
                continue
            else:
                yield log

    def cleanup(self):
        shutil.rmtree(self.code_copy_path)
        # Delete created image self.repository else it will clog up disk
        if os.environ.get("MODE") != "Local":
            remove_image(self.repository.lstrip("repository: "))