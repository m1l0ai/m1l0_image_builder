from unittest.mock import patch, Mock, PropertyMock
import pytest

from builder.service.imageservice import ImageBuilderService
from m1l0_services.imagebuilder.image_builder_pb2 import BuildRequest, BuildConfig


# @patch("builder.core.imagebuilder.ImageBuilder.repository", new_callable=PropertyMock)
# @patch("builder.core.imagebuilder.ImageBuilder.imagename", new_callable=PropertyMock)
@patch("builder.core.imagebuilder.ImageBuilder.cleanup_code_path")
@patch("builder.core.imagebuilder.ImageBuilder.build")
def test_builder_Build(mock_build, mock_cleanup):
    mock_build = Mock()
    # mock_build.__iter__ = Mock(return_value=iter(["80%", "90%", "100%"]))
    mock_build.iter.return_value = iter(["80%", "90%", "100%"])

    mock_cleanup = Mock()

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
    # TODO: No resp in body??
    # print(resp)