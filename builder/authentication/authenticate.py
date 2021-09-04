from docker.errors import APIError
import boto3
import base64


def get_ecr_image_prefix(auth_config):
    """
    Gets the account id of the current logged in user and builds a ECR image prefix
    """
    sts_client = boto3_client("sts", auth_config)
    # account_id = session.client('sts').get_caller_identity().get('Account')
    
    account_id = sts_client.get_caller_identity().get("Account")
    return "{}.dkr.ecr.{}.amazonaws.com".format(account_id, auth_config.get("region"))

def boto3_client(service, config):
    if all([config.get("region"), config.get("profile")]):
        return session_client(service, config)

    client = boto3.client(
        service,
        aws_access_key_id=config["AccessKeyId"],
        aws_secret_access_key=config["SecretAccessKey"],
        aws_session_token=config["Token"]
    )

    return client

def session_client(service, auth_config):
    """
    Creates and returns a boto3 session client
    """
    region = auth_config.get("region")
    profile = auth_config.get("profile")
    session = boto3.session.Session(profile_name=profile, region_name=region)

    return session.client(service)

def authenticate_ecr(auth_config, tag):
    """
    Authenticates with remote ECR service

    Takes project tag and returns formatted ECR repo name

    Inputs:
    auth_config => dict of aws creds
    tag => name of repository
    """
    # session = session_client(auth_config)
    # region = auth_config.get("region")
    # ecr_client = session.client("ecr", region_name=region)

    ecr_client = boto3_client("ecr", auth_config)

    ecr_prefix = get_ecr_image_prefix(auth_config)
    
    # ecr_prefix = get_ecr_image_prefix(session, region)

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