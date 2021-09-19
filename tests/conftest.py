import contextlib
import os
from pathlib import Path
import shutil
import tempfile

import boto3
from moto import mock_s3, mock_secretsmanager, mock_sts
import pytest


@pytest.fixture(scope='function')
def aws_credentials():
    """Mocked AWS Credentials for moto."""
    creds_path = os.path.join(str(Path(__file__).parent.absolute()), "dummy_creds")
    os.environ["AWS_SHARED_CREDENTIALS_FILE"] = creds_path


@pytest.fixture(scope='function')
def s3(aws_credentials):
    with mock_s3():
        yield boto3.client("s3", region_name='us-east-1')


@pytest.fixture(scope="function")
def ssm(aws_credentials):
    with mock_secretsmanager():
        yield boto3.client("secretsmanager", region_name='us-east-1')

@pytest.fixture(scope="function")
def sts(aws_credentials):
    with mock_sts():
        yield boto3.client("sts", region_name="us-east-1")

@pytest.fixture()
def create_tmp_directory():
    """
    Fixture to simulate how the code retriever would create
    directories

    We first create the orig directory and then a new dir
    with the id inside the /tmp/code folder to match application
    logic
    """
    @contextlib.contextmanager
    def _create_tmp(name, id, **kwargs):
        try:
            tmp_folder = os.path.join(tempfile.gettempdir(), name)
            # Create the original directory
            os.makedirs(tmp_folder)
            # Simulates creating the new directory
            new_dir = os.path.join(tempfile.gettempdir(), "code", id)

            yield (tmp_folder, new_dir)
        finally:
            if os.path.exists(tmp_folder):
                shutil.rmtree(tmp_folder)
            shutil.rmtree(new_dir, ignore_errors=True)

    return _create_tmp