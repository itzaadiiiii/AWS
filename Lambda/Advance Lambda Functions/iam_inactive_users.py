import boto3
import csv
import io
import time

from datetime import datetime, timezone

from common import send_notification


iam = boto3.client("iam")


# Generate the IAM credential report.
def generate_credential_report():

    try:
        iam.generate_credential_report()

    except iam.exceptions.ReportInProgressException:
        pass

    # Credential report generation is asynchronous.
    for attempt in range(12):

        response = iam.get_credential_report()

        if "Content" in response:

            return response["Content"].decode("utf-8")

        time.sleep(5)

    raise TimeoutError("IAM credential report not available")


def lambda_handler(event, context):

    # Inactivity threshold.
    threshold_days = event.get("threshold_days", 30)

    now = datetime.now(timezone.utc)

    report = generate_credential_report()

    csv_reader = csv.DictReader(io.StringIO(report))

    inactive_users = []

    for user in csv_reader:

        username = user["user"]

        # Do not process the root account.
        if username == "<root_account>":
            continue

        # Read last password and access-key activity.
        activity_fields = [
            "password_last_used",
            "access_key_1_last_used_date",
            "access_key_2_last_used_date"
        ]

        activity_dates = []

        for field in activity_fields:

            value = user.get(field)

            if value and value not in ("N/A", "no_information"):

                activity_dates.append(
                    datetime.fromisoformat(
                        value.replace("Z", "+00:00")
                    )
                )

        # No credential activity recorded.
        if not activity_dates:

            inactive_users.append({
                "username": username,
                "last_activity": "No activity recorded",
                "inactive_days": None
            })

            continue

        last_activity = max(activity_dates)

        inactive_days = (now - last_activity).days

        if inactive_days >= threshold_days:

            inactive_users.append({

                "username": username,

                "last_activity": last_activity.isoformat(),

                "inactive_days": inactive_days

            })

    # Send one consolidated report.
    if inactive_users:

        send_notification(
            "AWS IAM Inactive User Alert",
            {
                "threshold_days": threshold_days,
                "total_inactive_users": len(inactive_users),
                "users": inactive_users,
                "recommended_action": (
                    "Contact the identity owner and validate "
                    "whether access is still required."
                )
            }
        )

    return {
        "inactive_users": len(inactive_users),
        "details": inactive_users
    }
