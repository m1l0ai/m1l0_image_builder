import docker
from docker import APIClient

def docker_api_client(socket='unix://var/run/docker.sock'):
    """
    Returns a low level docker api client for building which returns progress status
    """
    return APIClient(base_url=socket)

def docker_client(version='1.40'):
    return docker.from_env(version=version)