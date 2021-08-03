import image_builder_pb2_grpc as image_builder_pb2_grpc
from image_builder_pb2 import BuildResponse, BuildLog
from core import GetSourceFiles, ImageBuilder
from concurrent import futures
import sys
import grpc
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

        # image_name, buildlogs = builder.build()

        builder = ImageBuilder(request, code_copy_path)

        for log in builder.build():
            yield BuildLog(body=log)

        for log in builder.push():
            yield BuildLog(body=log)

        builder.cleanup()

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