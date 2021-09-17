from grpc_interceptor.exceptions import InvalidArgument


class ServiceRequestValidator:
    """Validator for ImageService"""

    @staticmethod
    def validate(request):
        supported_services = ["dockerhub", "ecr"]
        if request.config.service not in supported_services:
            raise InvalidArgument("Service not one of dockerhub/ecr")

        if len(request.config.repository) == 0:
            raise InvalidArgument("Repository cannot be blank")