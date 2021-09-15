from unittest.mock import patch, Mock, PropertyMock
import pytest

from builder.service.imageservice import ImageBuilderService
from m1l0_services.imagebuilder.image_builder_pb2 import BuildRequest, BuildConfig


@patch("builder.core.imagebuilder.ImageBuilder.repository", new_callable=PropertyMock)
@patch("builder.core.imagebuilder.ImageBuilder.imagename", new_callable=PropertyMock)
@patch("builder.core.imagebuilder.ImageBuilder.cleanup")
@patch("builder.core.imagebuilder.ImageBuilder.push")
@patch("builder.core.imagebuilder.ImageBuilder.build")
def test_builder_build(mock_build, mock_push, mock_cleanup, mock_imgname, mock_repository):
    mock_build = Mock()
    mock_build.__iter__ = Mock(return_value=iter(["100%"]))
    mock_push = Mock()
    mock_push.__iter__ = Mock(return_value=iter(["100%"]))
    mock_cleanup = Mock()

    mock_imgname.return_value = "m1l0/myproject:latest"
    mock_repository.return_value = "m1l0/myproject:latest"

    config = {
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
    assert "m1l0/myproject:latest" in resp