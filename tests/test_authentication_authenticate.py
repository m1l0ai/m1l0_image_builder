from unittest.mock import patch, Mock, PropertyMock

from botocore.stub import Stubber
from docker import APIClient
from docker.errors import APIError
import pytest

from builder.authentication.authenticate import session_client, get_ecr_image_prefix, authenticate_docker_client

@patch("botocore.configloader.load_config")
def test_session_client(mock_profiles):
    mock_profiles.return_value = {"profiles": {"myprofile": {}}}
    profile = {"profile_name": "myprofile"}
    sess = session_client("sts", profile)
    type(sess).__name__ == "STS"

@patch("builder.authentication.authenticate.session_client")
def test_get_ecr_image_prefix(mock_session, sts):
    mock_session.return_value = sts

    rolearn = "arn:aws:iam::123456789012:role/demo"
    stubber = Stubber(sts)
    resp = {
        "Account": "56789"
    }
    
    stubber.add_response('get_caller_identity', resp, {})
    stubber.activate()

    res = get_ecr_image_prefix({"region": "us-east-1"})
    assert res == "56789.dkr.ecr.us-east-1.amazonaws.com"

@patch("docker.APIClient.login")
def test_authenticate_docker_client(mock_docker_client):
    mock_docker_client.return_value = {"Status": "Success"}

    client = APIClient()
    auth = {}
    resp = authenticate_docker_client(client, "mydocker/myproj:latest", auth)
    assert resp == "Success"
    assert auth["reauth"] == True
    assert auth["registry"] == "mydocker/myproj:latest"

    # Test for failed login
    with pytest.raises(APIError) as exc_info:
        mock_docker_client.side_effect = APIError("Issue with login")    
        client = APIClient()
        resp = authenticate_docker_client(client, "mydocker/myproj:latest", {})
    assert "Issue with login" in str(exc_info.value)