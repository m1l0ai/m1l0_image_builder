from unittest.mock import patch, Mock, PropertyMock

from grpc_interceptor.exceptions import InvalidArgument
import pytest

from builder.service.imageservice import ImageBuilderService
from m1l0_services.imagebuilder.image_builder_pb2 import BuildRequest, BuildConfig

@patch("builder.core.retriever.GetSourceFiles.call")
@patch("builder.core.imagebuilder.ImageBuilder.cleanup_code_path")
@patch("builder.core.imagebuilder.ImageBuilder.build")
def test_builder_Build(mock_build, mock_cleanup, mock_retriever):
    mock_build.return_value = iter(["80%", "90%", "100%"])
    mock_cleanup = Mock()
    mock_retriever.return_value = "/tmp/code/123"

    config = {
        "source": "dir:///tmp/123",
        "service": "dockerhub",
        "repository": "m1l0/myproject",
        "revision": "latest"
    }

    request = BuildRequest(
        id="123", 
        config=BuildConfig(**config)
    )

    service = ImageBuilderService()
    resp = service.Build(request, None)
    resp = [x.body for x in resp]
    assert resp == ["80%", "90%", "100%"]

    # Test failed retriever call
    mock_retriever.side_effect = Exception("Error with dir copy")
    with pytest.raises(Exception) as exc_info:
        service = ImageBuilderService()
        resp = service.Build(request, None)
        resp = [x.body for x in resp]
    assert "Error with dir copy" in str(exc_info.value)

@patch("builder.core.imagebuilder.ImageBuilder.cleanup_repository")
@patch("builder.core.imagebuilder.ImageBuilder.push")
def test_builder_Push(mock_push, mock_cleanup):
    mock_push.return_value = iter(["80%", "90%", "100%"])
    mock_cleanup = Mock()

    config = {
        "source": "dir:///tmp/123",
        "service": "dockerhub",
        "repository": "m1l0/myproject",
        "revision": "latest"
    }

    request = BuildRequest(
        id="123", 
        config=BuildConfig(**config)
    )

    service = ImageBuilderService()
    resp = service.Push(request, None)
    resp = [x.body for x in resp]
    assert resp == ["80%", "90%", "100%"]

    # Test invalid request
    with pytest.raises(InvalidArgument) as exc_info:
        config["service"] = "unknown"
        request = BuildRequest(
            id="123", 
            config=BuildConfig(**config)
        )
        service = ImageBuilderService()
        resp = service.Push(request, None)
        resp = [x.body for x in resp]

    assert "Service not one of dockerhub/ecr" in str(exc_info.value)