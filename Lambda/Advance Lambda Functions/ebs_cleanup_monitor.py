import boto3

from datetime import datetime, timezone

from common import send_notification


ec2 = boto3.client("ec2")


def lambda_handler(event, context):

    # Minimum volume age for reporting.
    threshold_days = 30

    now = datetime.now(timezone.utc)

    findings = []

    paginator = ec2.get_paginator("describe_volumes")

    # Find volumes with available status.
    for page in paginator.paginate(
        Filters=[
            {
                "Name": "status",
                "Values": ["available"]
            }
        ]
    ):

        for volume in page["Volumes"]:

            age_days = (
                now - volume["CreateTime"]
            ).days

            if age_days >= threshold_days:

                tags = {
                    tag["Key"]: tag["Value"]
                    for tag in volume.get("Tags", [])
                }

                findings.append({

                    "volume_id": volume["VolumeId"],

                    "size_gb": volume["Size"],

                    "age_days": age_days,

                    "environment": tags.get(
                        "Environment", "Unknown"
                    ),

                    "owner": tags.get(
                        "Owner", "Unknown"
                    ),

                    "action": "Review before deleting"

                })

    if findings:

        send_notification(
            "Unattached EBS Volume Report",
            {
                "total_volumes": len(findings),
                "volumes": findings
            }
        )

    return {
        "total_volumes": len(findings),
        "findings": findings
    }
