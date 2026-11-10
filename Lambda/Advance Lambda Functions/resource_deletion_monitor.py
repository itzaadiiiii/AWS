from common import send_notification


# AWS API deletion events to monitor.
DELETION_EVENTS = [
    "TerminateInstances",
    "DeleteVolume",
    "DeleteSnapshot",
    "DeleteSecurityGroup",
    "DeleteDBInstance",
    "DeleteBucket",
    "DeleteTrail",
    "ScheduleKeyDeletion"
]


def lambda_handler(event, context):

    detail = event.get("detail", {})

    event_name = detail.get("eventName")

    # Ignore events that aren't deletion events.
    if event_name not in DELETION_EVENTS:

        return {"status": "ignored"}

    # Identify who performed the action.
    identity = detail.get("userIdentity", {})

    username = (
        identity.get("userName")
        or identity.get("principalId")
        or "Unknown"
    )

    # Extract the affected resource details.
    request = detail.get("requestParameters", {})

    resources = detail.get("resources", [])

    notification = {

        "event": event_name,

        "performed_by": username,

        "account": event.get("account"),

        "region": event.get("region"),

        "timestamp": event.get("time"),

        "source_ip": detail.get("sourceIPAddress"),

        "request_parameters": request,

        "resources": resources,

        "action": "Verify whether deletion was authorized."

    }

    send_notification(
        "AWS Resource Deletion Detected",
        notification
    )

    return {
        "status": "notification_sent",
        "event": event_name
    }
