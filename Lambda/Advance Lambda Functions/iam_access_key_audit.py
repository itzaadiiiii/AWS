import boto3

from datetime import datetime, timezone

from common import send_notification


iam = boto3.client("iam")


def lambda_handler(event, context):

    # Organization-defined thresholds.
    warning_days = 60

    escalation_days = 90

    unused_days_threshold = 60

    now = datetime.now(timezone.utc)

    findings = []

    paginator = iam.get_paginator("list_users")

    for page in paginator.paginate():

        for user in page["Users"]:

            username = user["UserName"]

            # Retrieve all access keys belonging to the user.
            keys = iam.list_access_keys(
                UserName=username
            )["AccessKeyMetadata"]

            for key in keys:

                access_key = key["AccessKeyId"]

                created_date = key["CreateDate"]

                key_age = (now - created_date).days

                # Retrieve actual last-used information.
                usage = iam.get_access_key_last_used(
                    AccessKeyId=access_key
                )

                last_used = usage.get(
                    "AccessKeyLastUsed", {}
                ).get("LastUsedDate")

                unused_days = (
                    (now - last_used).days
                    if last_used else None
                )

                reasons = []

                if key_age >= escalation_days:

                    reasons.append("Key age exceeds 90 days")

                elif key_age >= warning_days:

                    reasons.append("Key age exceeds 60 days")

                if unused_days is None:

                    reasons.append("No last-used timestamp")

                elif unused_days >= unused_days_threshold:

                    reasons.append("Key unused for 60+ days")

                if reasons:

                    findings.append({

                        "username": username,

                        "access_key": (
                            access_key[:4] + "****" + access_key[-4:]
                        ),

                        "key_age_days": key_age,

                        "last_used": (
                            last_used.isoformat()
                            if last_used else "Never/no data"
                        ),

                        "unused_days": unused_days,

                        "status": key["Status"],

                        "reasons": reasons

                    })

    if findings:

        send_notification(
            "AWS Access Key Rotation Alert",
            {
                "total_findings": len(findings),
                "findings": findings,
                "action": "Review and rotate or retire eligible keys."
            }
        )

    return {
        "total_findings": len(findings),
        "findings": findings
    }
