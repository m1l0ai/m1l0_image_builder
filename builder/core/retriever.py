import logging
import os
import pkg_resources
from pathlib import Path
import shutil
import tarfile
import tempfile
import traceback
from urllib.parse import urlparse

from github import Github

from builder.authentication.authenticate import session_client
from builder.authentication.ssm import fetch_credentials

module_logger = logging.getLogger('builder.retriever')

class GetSourceFiles:
    """
    Fetches the source files and downloads them before building image
    """
    def __init__(self, request):
        self.request = request

    def call(self):
        parsed_url = urlparse(self.request.config.source)
        ignores = []

        if self.request.ignores:
            for ig in self.request.ignores:
                ignores.append(ig.value)

        tmp_path = os.path.join(tempfile.gettempdir(), "code")

        # normally this is a uuid
        code_path = self.request.id
        code_copy_path = os.path.join(tmp_path, code_path)

        if parsed_url.scheme == "dir":
            if not os.path.exists(parsed_url.path):
                raise Exception("Directory {} does not exist!".format(parsed_url.path))

            # Assume that the dir refers to an existing path inside the mounted volume of this container

            try:
                # Copy from parsed_url.path to temp dir to remove ignores
                shutil.move(parsed_url.path, code_copy_path + "_tmp")
                # Copy from temp back to code_copy_path
                shutil.copytree(code_copy_path + "_tmp", code_copy_path, ignore=shutil.ignore_patterns(*ignores))

                shutil.rmtree(code_copy_path + "_tmp")
            except Exception as e:
                error_msg = "Dir copy error: \n{}\n{}".format(traceback.format_exc(), str(e))
                module_logger.error(error_msg)
                raise e
        elif parsed_url.scheme == "s3":
            # Get token
            auth_config = fetch_credentials("ecr")
            s3_client = session_client("s3", auth_config)

            # Downloads from s3 bucket into local tmp folder..
            bucket = parsed_url.netloc
            s3_target = parsed_url.path.lstrip("/")
            local_target = f"{code_copy_path}.tar.gz"
            s3_client.download_file(bucket, s3_target, local_target)

            with tarfile.open(local_target) as t:
                t.extractall(code_copy_path + "_tmp")
            shutil.copytree(code_copy_path + "_tmp", code_copy_path, ignore=shutil.ignore_patterns(*ignores))

            shutil.rmtree(code_copy_path + "_tmp")
            os.remove(local_target)
        elif ".git" in parsed_url.path:
            # Get token
            auth_config = fetch_credentials("github")
            # Login to github first using token
            github_client = Github(auth_config["token"])
            repo = github_client.get_repo(parsed_url.path.lstrip("/").split(".git")[0])
            cmd = "git clone {} {}".format(repo.clone_url, code_copy_path + "_tmp")
            os.system(cmd)
            
            shutil.copytree(code_copy_path + "_tmp", code_copy_path, ignore=shutil.ignore_patterns(*ignores))

            shutil.rmtree(code_copy_path + "_tmp")

        return code_copy_path