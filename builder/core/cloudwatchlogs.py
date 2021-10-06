# Client lib to stream logs to cloudwatch
import json
import logging
import os
import time
import traceback

import boto3
from botocore.exceptions import ClientError

module_logger = logging.getLogger('builder.cloudwatch')

# Orig idea from: https://gist.github.com/olegdulin/fd18906343d75142a487b9a9da9042e0


def get_client(service):
    region = os.environ.get("AWS_DEFAULT_REGION")

    aws_container_credentials_uri = os.environ.get("AWS_CONTAINER_CREDENTIALS_RELATIVE_URI")

    if aws_container_credentials_uri:
        client = boto3.session.Session(region_name=region).client(service)
    else:
        profile = os.environ.get("AWS_PROFILE")
        client = boto3.session.Session(profile_name=profile, region_name=region).client(service)

    return client


def setup_log_stream(stream):
    """Creates the log stream"""
    log_group = os.environ.get("JOB_LOG_GROUP")

    client = get_client("logs")

    try:
        client.create_log_stream(
            logGroupName=log_group,
            logStreamName=stream
        )
    except client.exceptions.ResourceNotFoundException:
        # if log group does not exist we create it
        module_logger.info("Log group does not exist. Creating...")
        client.create_log_group(
            logGroupName=log_group
        )

        client.create_log_stream(
            logGroupName=log_group,
            logStreamName=stream
        )
    except client.exceptions.ResourceAlreadyExistsException:
        module_logger.info("Log group stream {} already exists".format(stream))


def send_to_cloudwatch(stream, events):
    """Write to log stream"""

    log_group = os.environ.get("JOB_LOG_GROUP")
    log_events = []
    for event in events:
        log_events.append({
            "timestamp": int(round(time.time() * 1000)),
            "message": json.dumps(event)
        })

    log_event = {
        "logGroupName": log_group,
        "logStreamName": stream,
        "logEvents": log_events
    }

    client = get_client("logs")

    try:
        client.put_log_events(**log_event)
    except client.exceptions.InvalidSequenceTokenException as e:
        log_event["sequenceToken"] = e.response["expectedSequenceToken"]

        try:
            client.put_log_events(**log_event)
        except ClientError as e:
            failure_msg = "\n{}\n{}".format(traceback.format_exc(), str(e))
            module_logger.error(failure_msg)
