import json
import os
from pathlib import Path
import shutil
import tarfile
import tempfile

from botocore.stub import Stubber
import pytest
from unittest.mock import patch, Mock, call

from builder.core.retriever import GetSourceFiles
from m1l0_services.imagebuilder.v1.imagebuilder_service_pb2 import BuildRequest, BuildResponse, BuildTags, BuildIgnores, BuildConfig

def test_non_existent_dir_raises_exception():
    request = BuildRequest(id="123", config=BuildConfig(source="dir:///tmp/test"))
    retriever = GetSourceFiles(request)

    # should raise exception of dir does not exist...
    with pytest.raises(Exception) as exc_info:
        retriever.call()

    assert str(exc_info.value) == "Directory /tmp/test does not exist!"

@patch("os.path.exists")
@patch("shutil.move")
def test_error_with_processing_dir(mock_shutil, mock_path):
    mock_path.return_value = True
    mock_shutil.side_effect = Exception("Dir copy error")
    request = BuildRequest(id="123", config=BuildConfig(source="dir:///tmp/test"))
    retriever = GetSourceFiles(request)

    # should raise exception of dir does not exist...
    with pytest.raises(Exception) as exc_info:
        retriever.call()

    assert str(exc_info.value) == "Dir copy error"

def test_dir_exists(create_tmp_directory):
    request = BuildRequest(id="123", config=BuildConfig(source="dir:///tmp/test"))
    retriever = GetSourceFiles(request)

    with create_tmp_directory("test", "123") as res:
        orig_dir, new_dir = res
        fpath = os.path.join(orig_dir, "hello")
        Path(fpath).touch()
        new_fpath = os.path.join(new_dir, 'hello')

        code_path = retriever.call()
        assert code_path == "/tmp/code/123"
        assert os.path.exists(new_dir) == True, "Moved to new directory"
        assert os.path.exists(new_fpath) == True, "Moved contents to new directory"

def test_dir_exists_with_ignores(create_tmp_directory):
    request = BuildRequest(id="123", config=BuildConfig(source="dir:///tmp/test"))

    for ig in ["*.txt", "__pycache__"]:
        ig2 = BuildIgnores(value=ig)
        request.ignores.append(ig2)

    retriever = GetSourceFiles(request)

    with create_tmp_directory("test", "123") as res:
        orig_dir, new_dir = res
        fpath = os.path.join(orig_dir, "hello.txt")
        dpath = os.path.join(orig_dir, "__pycache__")
        Path(fpath).touch()
        Path(dpath).mkdir(exist_ok=True)

        new_fpath = os.path.join(new_dir, 'hello.txt')
        new_dpath = os.path.join(new_dir, "__pycache__")

        code_path = retriever.call()
        assert code_path == "/tmp/code/123"
        assert os.path.exists(new_dir) == True, "Moved to new directory"
        assert os.path.exists(new_fpath) == False, "File should have been ignored"
        assert os.path.exists(new_dpath) == False, "Directory should have been ignored"

def test_s3_urls(ssm, s3, create_tmp_directory):
    os.environ.update({
        "SECRET_NAME": "secret", 
        "AWS_DEFAULT_REGION": "us-east-1",
        "AWS_PROFILE": "tester",
    })

    creds = json.dumps({
        "DOCKERHUB_TOKEN": "dtoken",
        "DOCKERHUB_USER": "m1l0",
        "GITHUB_TOKEN": "gtoken"
    })

    ssm.create_secret(
        Name="secret",
        SecretString=creds
    )

    # create s3 bucket
    s3.create_bucket(Bucket="mybucket")

    request = BuildRequest(id="123", config=BuildConfig(source="s3://mybucket/context.tar.gz"))
    retriever = GetSourceFiles(request)

    with create_tmp_directory("test", "123") as res:
        orig_dir, new_dir = res
        fpath = os.path.join(orig_dir, "hello")
        Path(fpath).touch()
        archive = os.path.join(orig_dir, "context.tar.gz")
        with tarfile.open(archive, mode="w:gz") as t:
            t.add(fpath, arcname=os.path.join(".", os.path.basename(fpath)))

        s3.upload_file(archive, "mybucket", "context.tar.gz")
        code_path = retriever.call()
        assert "hello" in os.listdir(code_path)

@patch("github.Github.get_repo")
@patch("os.system")
def test_github(fake_os, fake_git, ssm, create_tmp_directory):
    os.environ.update({
        "SECRET_NAME": "secret", 
        "AWS_DEFAULT_REGION": "us-east-1",
        "AWS_PROFILE": "tester",
    })

    creds = json.dumps({
        "DOCKERHUB_TOKEN": "dtoken",
        "DOCKERHUB_USER": "m1l0",
        "GITHUB_TOKEN": "gtoken"
    })

    ssm.create_secret(
        Name="secret",
        SecretString=creds
    )

    fake_git.return_value = Mock(clone_url="myrepo")
    fake_os.return_value = True

    request = BuildRequest(id="123", config=BuildConfig(source="https://github.com/myrepo.git"))
    retriever = GetSourceFiles(request)

    with create_tmp_directory("test", "123") as res:
        _, new_dir = res
        
        tmp_fpath = f"{new_dir}_tmp"
        os.makedirs(tmp_fpath, exist_ok=True)
        new_fpath = os.path.join(tmp_fpath, 'hello')
        Path(new_fpath).touch()

        code_path = retriever.call()
        assert code_path == "/tmp/code/123"
        assert os.path.exists(os.path.join(code_path, "hello")) == True, "Contents should have been moved to new directory"
        assert os.path.exists(code_path) == True, "Target directory should exist"
