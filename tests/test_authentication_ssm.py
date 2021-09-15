import json
import os

from botocore.exceptions import ClientError
from botocore.stub import Stubber
import pytest

from builder.authentication.ssm import fetch_credentials

def test_fetch_credentials(ssm):
    os.environ.update({
        "SECRET_NAME": "secret", 
        "AWS_DEFAULT_REGION": "us-east-1",
        "AWS_CONTAINER_CREDENTIALS_RELATIVE_URI": "http://localhost"
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

    config = fetch_credentials("dockerhub")
    assert config.get("username") == "m1l0"
    assert config.get("password") == "dtoken"

    config = fetch_credentials("github")
    assert config.get("token") == "gtoken"

    # Testing with "AWS_CONTAINER_CREDENTIALS_RELATIVE_URI"
    config = fetch_credentials("ecr")
    assert "region_name" in config.keys()
    assert config.get("region_name") == os.environ.get("AWS_DEFAULT_REGION")

    # Testing when running on localhost
    del os.environ["AWS_CONTAINER_CREDENTIALS_RELATIVE_URI"]
    os.environ.update({
        "AWS_PROFILE": "tester",
    })

    config = fetch_credentials("ecr")
    assert "profile_name" in config.keys()
    assert "region_name" in config.keys()
    assert config["profile_name"] == "tester"
    assert config["region_name"] == os.environ.get("AWS_DEFAULT_REGION")

    # test for error with SSM client api 
    os.environ["SECRET_NAME"] = "NA"
    with pytest.raises(ClientError) as exc_info:
        fetch_credentials("ecr")

    assert str(exc_info.value) == "An error occurred (ResourceNotFoundException) when calling the GetSecretValue operation: Secrets Manager can't find the specified secret."