from docker.errors import APIError
import boto3
import base64


def get_ecr_image_prefix(session, region='us-east-1'):
    """
    Gets the account id of the current logged in user and builds a ECR image prefix
    """
    account_id = session.client('sts').get_caller_identity().get('Account')
    return "{}.dkr.ecr.{}.amazonaws.com".format(account_id, region)


def authenticate_ecr(auth_config, tag):
    """
    Authenticates with remote ECR service

    Takes project tag and returns formatted ECR repo name

    Inputs:
    auth_config => dict of aws creds
    tag => name of repository
    """
    profile = auth_config.get("profile")
    region = auth_config.get("region")
    access_key = auth_config.get("access_key")
    secret_access_key = auth_config.get("secret_access_key")

    session = boto3.Session(aws_access_key_id=access_key, aws_secret_access_key=secret_access_key, profile_name=profile, region_name=region)
    ecr_client = session.client("ecr", region_name=region)
    ecr_prefix = get_ecr_image_prefix(session, region)

    login = ecr_client.get_authorization_token()
    b64token = login['authorizationData'][0]['authorizationToken'].encode('utf-8')
    ecr_username, ecr_password = base64.b64decode(b64token).decode('utf-8').split(':')
    ecr_url = login['authorizationData'][0]['proxyEndpoint']

    return ecr_url, {'username': ecr_username, 'password': ecr_password}

def authenticate_docker_client(docker_client, registry, auth_config):
    """
    Authenticates a Low-Level Docker API client to the given registry
    """
    try:
        args = auth_config
        args['reauth'] = True
        args['registry'] = registry
        resp = docker_client.login(**args)
        return resp['Status']
    except APIError as e:
        raise e