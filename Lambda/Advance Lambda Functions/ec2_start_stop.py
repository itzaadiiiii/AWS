# EC2 scheduled start/stop -
# Requirement: Automatically stop Dev and QA instances outside business hours.

# Only instances with the following tags are eligible:

# Environment = dev
# AutoSchedule = true


# Production instances are excluded.

import boto3
import os

from common import send_notification


ec2 = boto3.client("ec2")


# Safety: default to dry-run mode.
DRY_RUN = os.getenv("DRY_RUN", "true").lower() == "true"


def lambda_handler(event, context):

    action = event.get("action", "").lower()

    if action not in ["start", "stop"]:

        raise ValueError("Action must be start or stop")

    # Only development and QA environments are eligible.
    filters = [

        {
            "Name": "tag:Environment",
            "Values": ["dev", "qa"]
        },

        {
            "Name": "tag:AutoSchedule",
            "Values": ["true"]
        },

        {
            "Name": "instance-state-name",
            "Values": (
                ["stopped"] if action == "start"
                else ["running"]
            )
        }

    ]

    instances = []

    paginator = ec2.get_paginator("describe_instances")

    for page in paginator.paginate(Filters=filters):

        for reservation in page["Reservations"]:

            for instance in reservation["Instances"]:

                instances.append(instance["InstanceId"])

    if not instances:

        return {"message": "No eligible instances found"}

    # Execute only when dry-run is disabled.
    if not DRY_RUN:

        if action == "stop":

            ec2.stop_instances(
                InstanceIds=instances
            )

        else:

            ec2.start_instances(
                InstanceIds=instances
            )

    result = {

        "action": action,

        "instances": instances,

        "dry_run": DRY_RUN,

        "message": (
            "No changes made: dry run"
            if DRY_RUN
            else f"Requested EC2 {action}"
        )

    }

    send_notification(
        "EC2 Scheduled Automation Report",
        result
    )

    return result



# EventBridge Scheduler configuration:

# Schedule	Event input	Purpose
# Daily 9 PM	{"action":"stop"}	Stop Dev/QA
# Daily 9 AM	{"action":"start"}	Start Dev/QA

# Configure the timezone as Asia/Kolkata if your team follows Indian business hours.

# Set the Lambda environment variable DRY_RUN=false only after validating the selected instances and exclusions.
