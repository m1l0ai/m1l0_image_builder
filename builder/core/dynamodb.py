import logging
import os
import traceback

from builder.core.cloudwatchlogs import get_client
from botocore.exceptions import ClientError


module_logger = logging.getLogger('builder.dynamodb')

def update_image_record(img_id, attr_name, attr_val):
    """Updates the image record based on img_id and attr"""
    table_name = os.environ.get("M1L0_BUILDER_TABLE")
    client = get_client("dynamodb")

    try:
        resp = client.update_item(
            TableName=table_name,
            Key={
                "Id": {"S": img_id}
            },
            UpdateExpression=f"set {attr_name} = :val1",
            ExpressionAttributeValues={
                ":val1": {"S": attr_val}
            },
            ReturnValues="ALL_NEW"
        )
    except ClientError as e:
        failure_msg = "\n{}\n{}".format(traceback.format_exc(), str(e))
        module_logger.error(failure_msg)

def get_image_record(img_id):
    table_name = os.environ.get("M1L0_BUILDER_TABLE")
    client = get_client("dynamodb")

    try:
        resp = client.get_item(
            TableName=table_name,
            Key={
                "Id": {"S": img_id}
            }
        )

        return {
            "id": resp["Item"]["Id"]["S"],
            "image": resp["Item"]["ImageName"]["S"],
            "repository": resp["Item"]["Repository"]["S"]
        }
    except ClientError as e:
        failure_msg = "\n{}\n{}".format(traceback.format_exc(), str(e))
        module_logger.error(failure_msg)