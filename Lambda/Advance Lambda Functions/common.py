import boto3
import json
import os

from datetime import datetime, timezone


# SNS topic used for sending security and compliance alerts.
SNS_TOPIC_ARN = os.getenv("SNS_TOPIC_ARN")


def send_notification(subject, message):

    """
    Sends notifications through Amazon SNS.
    If SNS is not configured, logs the notification in CloudWatch.
    """

    print(json.dumps(message, default=str))

    if not SNS_TOPIC_ARN:
        return

    sns = boto3.client("sns")

    sns.publish(
        TopicArn=SNS_TOPIC_ARN,
        Subject=subject[:100],
        Message=json.dumps(message, indent=2, default=str)
    )


def get_account_details():

    """
    Retrieves the AWS account ID and current region.
    """

    sts = boto3.client("sts")

    account_id = sts.get_caller_identity()["Account"]

    region = boto3.session.Session().region_name

    return account_id, region


def get_current_time():

    return datetime.now(timezone.utc)
