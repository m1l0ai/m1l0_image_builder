import requests
import os
import sys


def iam_credentials():
    """Retrieves and sets the creds needed for running aws cli
    inside ECS container

    https://docs.aws.amazon.com/AmazonECS/latest/developerguide/task-iam-roles.html
    """

    aws_container_credentials_uri = os.environ.get("AWS_CONTAINER_CREDENTIALS_RELATIVE_URI", "")
    keyurl = "http://169.254.170.2{}".format(aws_container_credentials_uri)

    try:
        resp = requests.get(keyurl)
        resp.raise_for_status()
        output = resp.json()
        os.environ.update({
            "AWS_ACCESS_KEY_ID": output["AccessKeyId"],
            "AWS_SECRET_ACCESS_KEY": output["SecretAccessKey"],
            "AWS_SESSION_TOKEN": output["Token"]
        })
    except Exception as e:
        print('[TrainController Error] Error with getting IAM credentials: {}'.format(e), flush=True)
        sys.exit(1)
