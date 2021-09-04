import boto3
from botocore.exceptions import ClientError
import requests
import os
import base64
import json


def fetch_credentials(service):
    """
    Fetches the required creds from SSM service
    """
    secret_name = "m1l0/creds"

    aws_container_credentials_uri = os.environ.get("AWS_CONTAINER_CREDENTIALS_RELATIVE_URI")

    if aws_container_credentials_uri:
        keyurl = "http://169.254.170.2{}".format(aws_container_credentials_uri)

        resp = requests.get(keyurl)
        output = resp.json()

        ssm_client = boto3.client(
            "secretsmanager",
            aws_access_key_id=output["AccessKeyId"],
            aws_secret_access_key=output["SecretAccessKey"],
            aws_session_token=output["Token"]
        )
    else:
        profile = os.environ.get("AWS_PROFILE")
        region = os.environ.get("AWS_DEFAULT_REGION")
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
        if aws_container_credentials_uri:
            auth_config = {
              "AccessKeyId": output["AccessKeyId"],
              "SecretAccessKey": output["SecretAccessKey"],
              "Token": output["Token"]
            }
        else:
            auth_config = {
                "profile": profile, 
                "region": region
            }
    elif service == "github":
        auth_config = {
            "token": creds.get("GITHUB_TOKEN")
        }

    return auth_config
