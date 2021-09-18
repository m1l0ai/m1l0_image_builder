import os
from unittest.mock import patch, Mock, PropertyMock

import pytest
from m1l0_services.imagebuilder.image_builder_pb2 import BuildRequest, BuildConfig

from builder.core.imagebuilder import ImageBuilder

@patch("shutil.rmtree")
def test_cleanup_code_path(mock_shutil):
    mock_shutil.return_value = Mock()

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

    imagebuilder = ImageBuilder(request, code_copy_path="/tmp/code/123")
    imagebuilder.cleanup_code_path()
    mock_shutil.assert_called_with("/tmp/code/123")

@patch("docker.APIClient.remove_image")
def test_cleanup_repository(mock_remove_image):
    mock_remove_image.return_value = Mock()

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

    imagebuilder = ImageBuilder(request, code_copy_path="/tmp/code/123")
    imagebuilder._repository = "m1l0/myproject"
    imagebuilder.cleanup_repository()
    mock_remove_image.assert_called_with("m1l0/myproject", force=True)

def test_imagename_property():
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

    imagebuilder = ImageBuilder(request, code_copy_path="/tmp/code/123")
    imagebuilder._imagename = "m1l0/myproject"
    imagebuilder._repository = "m1l0/myproject"

    assert imagebuilder.imagename == "m1l0/myproject"
    assert imagebuilder.repository == "m1l0/myproject"