import boto3
from botocore.exceptions import ClientError
import os
import base64
import json


def fetch_credentials(service):
    """
    Fetches the required creds from SSM service
    """
    secret_name = "m1l0/creds"
    profile = os.environ.get("AWS_PROFILE")
    region = os.environ.get("AWS_REGION")
    session = boto3.session.Session(profile_name=profile, region_name=region)
    ssm_client = session.client("secretsmanager")

    try:
        get_secret_value_response = ssm_client.get_secret_value(
            SecretId=secret_name,
            VersionStage="AWSCURRENT"
        )["SecretString"]
    except ClientError as e:
        raise e

    creds = json.loads(get_secret_value_response)
    auth_config = dict()
    if service == "dockerhub":
        auth_config = {
            "username": creds.get("DOCKERHUB_USER"),
            "password": creds.get("DOCKERHUB_TOKEN")
        }
    elif service == "ecr":
        auth_config = {
            "profile": profile, 
            "region": region
        }
    elif service == "github":
        auth_config = {
            "token": creds.get("GITHUB_TOKEN")
        }

    return auth_config
