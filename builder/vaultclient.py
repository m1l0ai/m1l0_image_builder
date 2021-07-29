import requests
import os
import json

def unseal_vault():
    """
    Unseals the vault

    The unseal token will be passed into the service container as ENV vars
    """
    unseal_token = os.environ.get("VAULT_UNSEAL")
    resp = requests.post("http://127.0.0.1:8200/v1/sys/unseal", data=json.dumps({"key": unseal_token}))

    if resp.status_code == 200 and resp.json()["sealed"] == False:
        print("Vault unsealed")

def get_role_id(rolename):
    """
    Gets the role id of specific rolename
    """
    vault_token = os.environ.get("VAULT_TOKEN")
    headers = {"X-Vault-Token": vault_token}
    resp = requests.get("http://127.0.0.1:8200/v1/auth/approle/role/{}/role-id".format(rolename), headers=headers)
    if resp.status_code == 200:
        role_id = resp.json()["data"]["role_id"]
        return role_id

def create_role_secret(rolename):
    """
    Creates new secret under rolename
    """
    vault_token = os.environ.get("VAULT_TOKEN")
    headers = {"X-Vault-Token": vault_token}
    resp = requests.post("http://127.0.0.1:8200/v1/auth/approle/role/{}/secret-id".format(rolename), headers=headers)
    if resp.status_code == 200:
        secret_id = resp.json()["data"]["secret_id"]
        return secret_id

def approle_login(role_id, secret_id):
    """
    Logins to given approle using role_id and secret_id
    """
    data = {"role_id": role_id, "secret_id": secret_id}
    resp = requests.post("http://127.0.0.1:8200/v1/auth/approle/login", data=json.dumps(data))

    if resp.status_code == 200:
        client_token = resp.json()["auth"]["client_token"]
        return client_token

def get_secret(secret_name, token):
    """
    Gets the secret denoted by name
    """
    headers = {"X-Vault-Token": token}
    resp = requests.get("http://127.0.0.1:8200/v1/secret/data/{}".format(secret_name), headers=headers)

    if resp.status_code == 200:
        creds = resp.json()["data"]["data"]
        return creds

def fetch_credentials(service):
    """
    Wrapper function to call get_secret but only return subset of creds
    """
    rolename = os.environ.get("VAULT_APPROLE")
    secretname = os.environ.get("VAULT_SECRET")

    role_id = get_role_id(rolename)
    secret_id = create_role_secret(rolename)
    token = approle_login(role_id, secret_id)
    creds = get_secret(secretname, token)

    auth_config = dict()
    if service == "dockerhub":
        auth_config = {
            "username": creds.get("dockerhub_user"),
            "password": creds.get("dockerhub_token")
        }
    elif service == "ecr":
        auth_config = {
            "profile": creds.get("aws_profile"), 
            "region": creds.get("aws_region"),
            "access_key": creds.get("aws_access_key"),
            "secret_access_key": creds.get("aws_secret_key")
        }
    elif service == "github":
        auth_config = {
            "token": creds.get("github_token")
        }

    return auth_config



if __name__ == "__main__":
    unseal_vault()
    res = fetch_credentials("github")
    print(res)