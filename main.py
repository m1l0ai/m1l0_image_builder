from builder.service.imageservice import serve
import logging


logging.basicConfig(level=logging.INFO)
module_logger = logging.getLogger("builder")


if __name__ == "__main__":
    module_logger.info("Starting ImageBuilder service on port 50051 ...")
    serve()