# Core classes for building images
from builder.authentication.vaultclient import fetch_credentials, unseal_vault
from .repo import create_dockerfile, prepare_archive, build_docker_image, push_docker_image
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

        for log in build_docker_image(build_context, tag, labels, self.config):
            if "imagename:" in log:
                self.imagename = log
                continue
            else:
                yield log

    def push(self):
        tag = "{}/{}:{}".format(self.config.get("namespace"), self.config.get("name"), self.config.get("revision"))

        for log in push_docker_image(tag, self.config.get("service"), self.config.get("repository")):
            if "repository:" in log:
                self.repository = log
                continue
            else:
                yield log

    def cleanup(self):
        shutil.rmtree(self.code_copy_path)