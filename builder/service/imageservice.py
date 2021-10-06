import base64
from concurrent import futures
import logging
import os
import sys
from signal import signal, SIGTERM, SIGINT

import grpc
from grpc_health.v1 import health
from grpc_health.v1 import health_pb2
from grpc_health.v1 import health_pb2_grpc
from grpc_reflection.v1alpha import reflection
from m1l0_services.imagebuilder.v1 import imagebuilder_service_pb2_grpc
from m1l0_services.imagebuilder.v1 import imagebuilder_service_pb2
from m1l0_services.imagebuilder.v1.imagebuilder_service_pb2 import BuildResponse, FindResponse, PushResponse

from builder.core.retriever import GetSourceFiles
from builder.core.imagebuilder import ImageBuilder
from builder.validator.service_request_validator import ServiceRequestValidator


logging.basicConfig(level=logging.INFO)
module_logger = logging.getLogger("builder")
console_handler = logging.StreamHandler()
formatter = logging.Formatter(fmt='%(asctime)s: %(levelname)-8s %(message)s')
console_handler.setFormatter(formatter)
module_logger.addHandler(console_handler)


class ImageBuilderService(imagebuilder_service_pb2_grpc.ImageBuilderServiceServicer):
    def Build(self, request, context):
        module_logger.info("Received build request...")

        # Validate request
        ServiceRequestValidator.validate(request)

        code_copy_path = GetSourceFiles(request).call()
        builder = ImageBuilder(request, code_copy_path)

        for log in builder.build():
            yield BuildResponse(body=log)

        builder.cleanup_code_path()

    def Push(self, request, context):
        module_logger.info("Received push request...")
        # Validate request
        ServiceRequestValidator.validate(request)

        builder = ImageBuilder(request)

        for log in builder.push():
            yield PushResponse(body=log)

        builder.cleanup_repository()

    def Find(self, request, context):
        module_logger.info("Received query request...")
        resp = FindResponse()
        return resp


def serve(host, port, secure=False, local=False):
    server = grpc.server(
        futures.ThreadPoolExecutor(max_workers=10),
    )

    imagebuilder_service_pb2_grpc.add_ImageBuilderServiceServicer_to_server(ImageBuilderService(), server)

    listen_address = "{}:{}".format(host, port)

    if secure:
        if os.environ.get("MODE") == "Local":
            cert_path = os.path.join(os.getcwd(), "certs")

            with open(os.path.join(cert_path, "server-key.pem"), "rb") as f:
                server_key = f.read()

            with open(os.path.join(cert_path, "server-cert.pem"), "rb") as f:
                server_crt = f.read()
        else:
            # Check if ENV var set for the keys
            # if so we base64 decode them
            b64server_key = os.environ.get("M1L0_BUILDER_KEY")
            b64server_crt = os.environ.get("M1L0_BUILDER_CERT")
            b64server_ca = os.environ.get("M1L0_BUILDER_CA_CERT")

            if not all([b64server_key, b64server_crt]):
                raise RuntimeError("No private key and certificate found.")
            else:
                server_key = base64.b64decode(b64server_key)
                server_crt = base64.b64decode(b64server_crt)
                ca_crt = base64.b64decode(b64server_ca)
                ca_path = os.environ.get("M1L0_BUILDER_CA_PATH")

                if not os.path.exists("/certs"):
                    os.makedirs("/certs")

                with open(ca_path, "wb") as f:
                    f.write(ca_crt)

        creds = grpc.ssl_server_credentials([(server_key, server_crt)],         require_client_auth=False)
        server.add_secure_port(listen_address, creds)
    else:
        server.add_insecure_port(listen_address)

    def handle_sigterm(*_):
        module_logger.info("Received shutdown...")
        all_rpcs_done_event = server.stop(30)
        all_rpcs_done_event.wait(30)
        module_logger.info("Shutdown gracefully...")
        sys.exit(0)

    signal(SIGTERM, handle_sigterm)
    signal(SIGINT, handle_sigterm)

    # Starting healthcheck service...
    health_servicer = health.HealthServicer(
        experimental_non_blocking=True,
        experimental_thread_pool=futures.ThreadPoolExecutor(
            max_workers=10))

    health_pb2_grpc.add_HealthServicer_to_server(health_servicer, server)

    services = tuple(
        service.full_name
        for service in imagebuilder_service_pb2.DESCRIPTOR.services_by_name.values()) + (
            reflection.SERVICE_NAME, health.SERVICE_NAME)

    module_logger.info("Services > {}".format(services))
    for service in services:
        health_servicer.set(service, health_pb2.HealthCheckResponse.SERVING)

    # Need to enable reflection below to allow use of grpcurl
    reflection.enable_server_reflection(services, server)

    server.start()
    server.wait_for_termination()
