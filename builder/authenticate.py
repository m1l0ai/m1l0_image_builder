import base64
from docker.errors import APIError


def ecr_login(client, tag):
    """
    Authenticates with remote ECR service

    Takes project tag and returns formatted ECR repo name

    Inputs:
    client => ECR client
    """
    login = client.get_authorization_token()
    b64token = login['authorizationData'][0]['authorizationToken'].encode('utf-8')
    ecr_username, ecr_password = base64.b64decode(b64token).decode('utf-8').split(':')
    ecr_url = login['authorizationData'][0]['proxyEndpoint']

    ecr_repo_name = '{}/{}'.format(ecr_url.replace('https://', ''), tag)
    return ecr_url, ecr_repo_name, {'username': ecr_username, 'password': ecr_password}

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