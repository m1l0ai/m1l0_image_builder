from m1l0_services.imagebuilder import image_builder_pb2_grpc
from m1l0_services.imagebuilder import image_builder_pb2
from m1l0_services.imagebuilder.image_builder_pb2 import BuildResponse, BuildLog
from builder.core.retriever import GetSourceFiles
from builder.core.imagebuilder import ImageBuilder
from concurrent import futures
import sys
import grpc
from grpc_health.v1 import health
from grpc_health.v1 import health_pb2
from grpc_health.v1 import health_pb2_grpc
from grpc_reflection.v1alpha import reflection
from signal import signal, SIGTERM, SIGINT
import logging


logging.basicConfig(level=logging.INFO)
module_logger = logging.getLogger("builder")


class ImageBuilderService(image_builder_pb2_grpc.ImageBuilderServicer):
    def Build(self, request, context):
        module_logger.info("Received build request...")
        # print(request)
        # print(context)
        code_copy_path = GetSourceFiles(request).call()

        builder = ImageBuilder(request, code_copy_path)

        for log in builder.build():
            yield BuildLog(body=log)

        for log in builder.push():
            yield BuildLog(body=log)

        for item in [builder.imagename, builder.repository]:
            yield BuildLog(body=item)

        builder.cleanup()

def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))

    image_builder_pb2_grpc.add_ImageBuilderServicer_to_server(ImageBuilderService(), server)

    server.add_insecure_port("[::]:50051")

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
        for service in image_builder_pb2.DESCRIPTOR.services_by_name.values()) + (
            reflection.SERVICE_NAME, health.SERVICE_NAME)

    module_logger.info("Services > {}".format(services))
    for service in services:
        health_servicer.set(service, health_pb2.HealthCheckResponse.SERVING)

    
    # Need to enable reflection below to allow use of grpcurl
    reflection.enable_server_reflection(services, server)

    server.start()
    server.wait_for_termination()

if __name__ == "__main__":
    module_logger.info("Starting ImageBuilder service....")
    serve()