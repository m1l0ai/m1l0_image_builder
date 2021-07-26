import image_builder_pb2_grpc as image_builder_pb2_grpc
from image_builder_pb2 import BuildRequest, BuildResponse, BuildTags
from concurrent import futures
import sys
import grpc
from signal import signal, SIGTERM, SIGINT
import logging
from urllib.parse import urlparse
import os
import tempfile
import shutil
import pkg_resources
from builder.repo import create_dockerfile, prepare_archive, build_docker_image, push_docker_image
from builder.vaultclient import fetch_credentials


logging.basicConfig(level=logging.INFO)
module_logger = logging.getLogger("builder")


class ImageBuilderService(image_builder_pb2_grpc.ImageBuilderServicer):
    def Build(self, request, context):
        module_logger.info("Received build request...")
        # print(request)
        # print(context)

        parsed_url = urlparse(request.source)
        ignores = []
        labels = {}

        if request.ignores:
            for ig in request.ignores:
                ignores.append(ig.value)

        if request.tags:
            for tag in request.tags:
                labels[tag.name] = tag.value

        if parsed_url.scheme == "file":
            tmp_path = os.path.join(tempfile.gettempdir(), "code")
            if os.path.exists(tmp_path):
                shutil.rmtree(tmp_path)

            code_path = "codeobjs"
            code_copy_path = os.path.join(tmp_path, "codeobjs")
            shutil.copytree(parsed_url.path, code_copy_path, ignore=shutil.ignore_patterns(*ignores))

            has_requirements = False
            files_list = os.listdir(code_copy_path)
            if "requirements.txt" in files_list:
                has_requirements = True

            config = {
                "namespace": request.namespace,
                "name": request.name,
                "framework": request.framework,
                "version": request.version,
                "pyversion": request.pyversion,
                "resource": request.resource,
                "entry": request.entry,
                "tags": labels,
                "revision": request.revision,
                "service": request.service,
                "repository": request.repository
            }

            tmpl_dir = pkg_resources.resource_filename("builder", "templates")
            dockerfile, builder_img = create_dockerfile(config, tmpl_dir, code_path, tmp_path, has_requirements=has_requirements, save_file=False)

            build_context = prepare_archive(dockerfile, code_copy_path)

            tag = "{}/{}:{}".format(config["namespace"], config["name"], config["revision"])
            image_name = build_docker_image(build_context, tag, labels, builder_img)

            # TODO: How to retrieve service creds
            auth_config = fetch_credentials(config["service"])
            repository_name = push_docker_image(tag, config["service"], auth_config, config.get("repository"))

            shutil.rmtree(tmp_path)


        return BuildResponse(image=image_name, repository=repository_name)

def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))

    image_builder_pb2_grpc.add_ImageBuilderServicer_to_server(ImageBuilderService(), server)

    server.add_insecure_port("[::]:50051")
    server.start()

    def handle_sigterm(*_):
        module_logger.info("Received shutdown...")
        all_rpcs_done_event = server.stop(30)
        all_rpcs_done_event.wait(30)
        module_logger.info("Shutdown gracefully...")
        sys.exit(0)

    signal(SIGTERM, handle_sigterm)
    signal(SIGINT, handle_sigterm)

    server.wait_for_termination()

if __name__ == "__main__":
    module_logger.info("Starting ImageBuilder service....")
    serve()