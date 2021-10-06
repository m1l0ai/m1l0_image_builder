import pytest

from grpc_interceptor.exceptions import InvalidArgument

from m1l0_services.imagebuilder.v1.imagebuilder_service_pb2 import BuildRequest, BuildConfig
from builder.validator.service_request_validator import ServiceRequestValidator


def test_valid_request():
    config = {
        "source": "/tmp/123",
        "service": "dockerhub",
        "repository": "m1l0/myproject",
        "revision": "latest"
    }

    request = BuildRequest(
        id="123", 
        config=BuildConfig(**config)
    )

    # Assert no exception raised
    assert ServiceRequestValidator.validate(request) is None

def test_invalid_service():
    config = {
        "service": "unknown",
        "repository": "m1l0/myproject",
        "revision": "latest"
    }

    request = BuildRequest(
        id="123", 
        config=BuildConfig(**config)
    )

    with pytest.raises(InvalidArgument) as exc_info:
        ServiceRequestValidator.validate(request)
    assert "Service not one of dockerhub/ecr" in str(exc_info.value)

def test_invalid_missing_repository():
    config = {
        "service": "ecr",
        "revision": "latest"
    }

    request = BuildRequest(
        id="123", 
        config=BuildConfig(**config)
    )

    with pytest.raises(InvalidArgument) as exc_info:
        ServiceRequestValidator.validate(request)
    assert "Repository cannot be blank" in str(exc_info.value)

def test_invalid_missing_source():
    config = {
        "service": "ecr",
        "revision": "latest",
        "repository": "m1l0/myproject"
    }

    request = BuildRequest(
        id="123", 
        config=BuildConfig(**config)
    )

    with pytest.raises(InvalidArgument) as exc_info:
        ServiceRequestValidator.validate(request)
    assert "Source cannot be blank" in str(exc_info.value)