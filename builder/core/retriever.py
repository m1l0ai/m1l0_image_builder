from github import Github
import tempfile
import os
import shutil
from urllib.parse import urlparse
import pkg_resources
from pathlib import Path
import traceback
from builder.authentication.authenticate import session_client
from builder.authentication.vaultclient import fetch_credentials, unseal_vault



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

        # normally this is a uuid
        code_path = self.request.id
        code_copy_path = os.path.join(tmp_path, code_path)

        if parsed_url.scheme == "dir":
            if not os.path.exists(parsed_url.path):
                raise Exception("Directory {} does not exist!".format(parsed_url.path))

            # Assume that the dir refers to an existing path inside the mounted volume of this container

            try:
                # Copy from parsed_url.path to temp dir to remove ignores
                # shutil.move(parsed_url.path, code_copy_path + "_tmp")
                # # Copy from temp back to code_copy_path
                # shutil.copytree(code_copy_path + "_tmp", code_copy_path, ignore=shutil.ignore_patterns(*ignores))

                # shutil.rmtree(code_copy_path + "_tmp")


                shutil.copytree(parsed_url.path, code_copy_path, ignore=shutil.ignore_patterns(*ignores))
                shutil.rmtree(parsed_url.path)
            except Exception as e:
                error_msg = "Dir copy error: \n{}\n{}".format(traceback.format_exc(), str(e))
                print(error_msg)
        elif parsed_url.scheme == "s3":
            # TODO
            # path will be compressed tar archive
            # need to extract


            # Get token
            unseal_vault()
            auth_config = fetch_credentials("ecr")
            s3_client = session_client(auth_config).client("s3")
            # Downloads from s3 bucket into local tmp folder..
            


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