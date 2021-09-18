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

@patch("builder.core.imagebuilder.build_docker_image")
@patch("builder.core.imagebuilder.prepare_archive")
@patch("builder.core.imagebuilder.create_dockerfile")
@patch("os.listdir")
def test_build(mock_listdir, mock_docker, mock_archive, mock_builder):
    mock_listdir.return_value = iter(["main.py"])
    mock_docker.return_value = "DOCKERFILE CONTENTS"
    mock_archive.return_value = "test.tar.gz"
    mock_builder.return_value = iter(["80%", "90%", "100%", "imagename: m1l0/myproject"])

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

    res = imagebuilder.build()
    res = list(res)
    assert res == ["80%", "90%", "100%"]
    assert imagebuilder.imagename == 'imagename: m1l0/myproject'

@patch("builder.core.imagebuilder.push_docker_image")
def test_push(mock_push):
    mock_push.return_value = iter(["80%", "90%", "100%", "repository: m1l0/myproject"])

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
    res = imagebuilder.push()
    res = list(res)
    assert res == ["80%", "90%", "100%"]
    assert imagebuilder.repository == "repository: m1l0/myproject"