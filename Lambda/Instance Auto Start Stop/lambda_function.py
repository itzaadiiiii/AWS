import logging
import os

import boto3

logger = logging.getLogger()
logger.setLevel(logging.INFO)

ec2 = boto3.client("ec2")

TAG_KEY = os.environ.get("TAG_KEY", "Environment")
ENVIRONMENTS = [e.strip() for e in os.environ.get("ENVIRONMENTS", "Dev,QA,Stage").split(",")]
# Instances carrying this tag with value "true" are never touched
SKIP_TAG = os.environ.get("SKIP_TAG", "SchedulerSkip")


def _target_instances(states):
    """Return IDs of tagged instances in the given states, minus opt-outs and ASG members."""
    paginator = ec2.get_paginator("describe_instances")
    filters = [
        {"Name": f"tag:{TAG_KEY}", "Values": ENVIRONMENTS},
        {"Name": "instance-state-name", "Values": states},
    ]
    ids = []
    for page in paginator.paginate(Filters=filters):
        for reservation in page["Reservations"]:
            for inst in reservation["Instances"]:
                tags = {t["Key"]: t["Value"] for t in inst.get("Tags", [])}
                if tags.get(SKIP_TAG, "").lower() == "true":
                    logger.info("Skipping %s (opt-out tag)", inst["InstanceId"])
                    continue
                if "aws:autoscaling:groupName" in tags:
                    logger.info("Skipping %s (ASG-managed)", inst["InstanceId"])
                    continue
                if inst.get("InstanceLifecycle") == "spot":
                    logger.info("Skipping %s (spot)", inst["InstanceId"])
                    continue
                ids.append(inst["InstanceId"])
    return ids


def _chunks(items, size=100):
    for i in range(0, len(items), size):
        yield items[i:i + size]


def lambda_handler(event, context):
    action = (event or {}).get("action", "").lower()
    if action not in ("start", "stop"):
        raise ValueError(f"event.action must be 'start' or 'stop', got: {action!r}")

    states = ["running"] if action == "stop" else ["stopped"]
    ids = _target_instances(states)
    logger.info("action=%s environments=%s matched=%d ids=%s", action, ENVIRONMENTS, len(ids), ids)

    done, failed = [], []
    for batch in _chunks(ids):
        try:
            if action == "stop":
                ec2.stop_instances(InstanceIds=batch)
            else:
                ec2.start_instances(InstanceIds=batch)
            done.extend(batch)
        except Exception:
            # e.g. InsufficientInstanceCapacity - retry one by one so one bad instance doesn't block the rest
            logger.exception("Batch %s failed, retrying individually", batch)
            for iid in batch:
                try:
                    (ec2.stop_instances if action == "stop" else ec2.start_instances)(InstanceIds=[iid])
                    done.append(iid)
                except Exception:
                    logger.exception("Failed to %s %s", action, iid)
                    failed.append(iid)

    result = {"action": action, "succeeded": done, "failed": failed}
    logger.info(result)
    if failed:
        # surface in CloudWatch metrics / alarms
        raise RuntimeError(f"Failed to {action}: {failed}")
    return result
