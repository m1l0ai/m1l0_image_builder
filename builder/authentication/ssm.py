import json
import os

import boto3
from botocore.exceptions import ClientError


def fetch_local_credentials(service):
    auth_config = dict()

    if service == "dockerhub":
        auth_config = {
            "username": os.environ.get("TF_VAR_DOCKERHUB_USER"),
            "password": os.environ.get("TF_VAR_DOCKERHUB_TOKEN")
        }
    elif service == "ecr":
        auth_config = {
            "profile_name": os.environ.get("AWS_PROFILE"),
            "region_name": os.environ.get("AWS_DEFAULT_REGION")
        }
    elif service == "github":
        auth_config = {
            "token": os.environ.get("TF_VAR_GITHUB_TOKEN")
        }

    return auth_config


def fetch_credentials(service):
    """
    Fetches the required creds from SSM service
    """
    if os.environ.get("MODE") == "Local":
        return fetch_local_credentials(service)

    secret_name = os.environ.get("SECRET_NAME")
    region = os.environ.get("AWS_DEFAULT_REGION")

    aws_container_credentials_uri = os.environ.get("AWS_CONTAINER_CREDENTIALS_RELATIVE_URI")

    if aws_container_credentials_uri:
        ssm_client = boto3.session.Session(region_name=region).client("secretsmanager")
    else:
        profile = os.environ.get("AWS_PROFILE")
        ssm_client = boto3.session.Session(profile_name=profile, region_name=region).client("secretsmanager")

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
        if aws_container_credentials_uri:
            auth_config = {
                "region_name": region
            }
        else:
            auth_config = {
                "profile_name": profile,
                "region_name": region
            }
    elif service == "github":
        auth_config = {
            "token": creds.get("GITHUB_TOKEN")
        }

    return auth_config
