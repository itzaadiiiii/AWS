
readme_content = """# EC2 Instance Stopper Lambda

A Python AWS Lambda function that stops EC2 instances filtered by a `PrivateIP` tag. Built with error handling, pagination, dry-run support, and structured logging.

---

## Table of Contents

- [Features](#features)
- [Prerequisites](#prerequisites)
- [Deployment](#deployment)
- [Configuration](#configuration)
- [Usage](#usage)
- [IAM Permissions](#iam-permissions)
- [Function Code](#function-code)
- [Event Payloads](#event-payloads)
- [Response Format](#response-format)
- [Monitoring](#monitoring)
- [License](#license)

---

## Features

| Feature | Description |
|---------|-------------|
| **Pagination** | Handles paginated `describe_instances` responses — no instances missed |
| **Error Handling** | Graceful `ClientError` catching with structured error responses |
| **Dry-Run Mode** | Validate permissions and logic without actually stopping instances |
| **State Filtering** | Skips already stopped/stopping instances to avoid redundant API calls |
| **Structured Logging** | CloudWatch-compatible logs for debugging and auditing |
| **Event-Driven Config** | Override target IP and dry-run flag via event payload |
| **Detailed Response** | Returns previous and current instance states |

---

## Prerequisites

- AWS Account
- IAM Role with EC2 permissions (see [IAM Permissions](#iam-permissions))
- Python 3.9+ runtime for Lambda

---

## Deployment

### 1. Create the Lambda Function

```bash
aws lambda create-function \\
    --function-name ec2-instance-stopper \\
    --runtime python3.11 \\
    --role arn:aws:iam::<ACCOUNT_ID>:role/<LAMBDA_ROLE> \\
    --handler lambda_function.lambda_handler \\
    --zip-file fileb://lambda.zip \\
    --timeout 30 \\
    --memory-size 128
```

### 2. Or use AWS Console

1. Go to **Lambda > Functions > Create function**
2. Choose **Author from scratch**
3. Runtime: **Python 3.11**
4. Paste the code from [Function Code](#function-code)
5. Set handler: `lambda_function.lambda_handler`
6. Attach IAM role with required permissions

---

## Configuration

The function uses the following defaults, all overridable via the event payload:

| Parameter | Default | Description |
|-----------|---------|-------------|
| `privateIp` | `"172.31.34.141"` | The `PrivateIP` tag value to filter instances |
| `dryRun` | `false` | If `true`, validates without stopping instances |

---

## Usage

### Invoke via AWS CLI

```bash
aws lambda invoke \\
    --function-name ec2-instance-stopper \\
    --payload '{"privateIp":"172.31.34.141","dryRun":false}' \\
    response.json
```

### Invoke via AWS Console

1. Go to **Lambda > Functions > ec2-instance-stopper**
2. Click **Test**
3. Create a new test event with your payload
4. Click **Test**

---

## IAM Permissions

Attach this policy to the Lambda execution role:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "ec2:DescribeInstances",
                "ec2:StopInstances"
            ],
            "Resource": "*"
        },
        {
            "Effect": "Allow",
            "Action": [
                "logs:CreateLogGroup",
                "logs:CreateLogStream",
                "logs:PutLogEvents"
            ],
            "Resource": "arn:aws:logs:*:*:*"
        }
    ]
}
```

---

## Function Code

Save as `lambda_function.py`:

```python
import boto3
import logging
from botocore.exceptions import ClientError

logger = logging.getLogger()
logger.setLevel(logging.INFO)

ec2 = boto3.client("ec2")


def lambda_handler(event, context):
    \"\"\"
    Stops EC2 instances filtered by the 'PrivateIP' tag.

    Expected event format (optional):
    {
        "dryRun": false,              # Set to true to validate without stopping
        "privateIp": "172.31.34.141"  # Override the default IP
    }
    \"\"\"
    # --- Configuration ---
    target_ip = event.get("privateIp", "172.31.34.141")
    dry_run = event.get("dryRun", False)

    logger.info(f"Looking for instances with tag PrivateIP={target_ip}")
    if dry_run:
        logger.info("DRY RUN mode enabled — no instances will be stopped")

    # --- Find instances ---
    instance_ids = []
    next_token = None

    try:
        while True:
            kwargs = {
                "Filters": [
                    {"Name": "tag:PrivateIP", "Values": [target_ip]}
                ]
            }
            if next_token:
                kwargs["NextToken"] = next_token

            response = ec2.describe_instances(**kwargs)

            for reservation in response.get("Reservations", []):
                for instance in reservation.get("Instances", []):
                    instance_id = instance["InstanceId"]
                    state = instance["State"]["Name"]

                    # Skip already stopped or stopping instances
                    if state in ("stopped", "stopping"):
                        logger.info(f"Skipping {instance_id} (already {state})")
                        continue

                    instance_ids.append(instance_id)
                    logger.info(f"Found instance {instance_id} (state: {state})")

            next_token = response.get("NextToken")
            if not next_token:
                break

    except ClientError as e:
        logger.error(f"Failed to describe instances: {e}")
        return {
            "statusCode": 500,
            "error": str(e),
            "StoppedInstances": []
        }

    # --- Stop instances ---
    stopped_instances = []

    if not instance_ids:
        logger.info("No running instances found to stop")
        return {
            "statusCode": 200,
            "StoppedInstances": [],
            "message": "No instances found matching criteria"
        }

    try:
        logger.info(f"Stopping instances: {instance_ids}")

        stop_response = ec2.stop_instances(
            InstanceIds=instance_ids,
            DryRun=dry_run
        )

        for state_change in stop_response.get("StoppingInstances", []):
            stopped_instances.append({
                "InstanceId": state_change["InstanceId"],
                "PreviousState": state_change["PreviousState"]["Name"],
                "CurrentState": state_change["CurrentState"]["Name"]
            })
            logger.info(
                f"Instance {state_change['InstanceId']}: "
                f"{state_change['PreviousState']['Name']} -> {state_change['CurrentState']['Name']}"
            )

    except ClientError as e:
        error_code = e.response["Error"]["Code"]
        if error_code == "DryRunOperation":
            logger.info("DryRun validation successful")
            return {
                "statusCode": 200,
                "DryRun": True,
                "WouldStop": instance_ids
            }
        logger.error(f"Failed to stop instances: {e}")
        return {
            "statusCode": 500,
            "error": str(e),
            "StoppedInstances": []
        }

    return {
        "statusCode": 200,
        "StoppedInstances": stopped_instances,
        "DryRun": dry_run
    }
```

---

## Event Payloads

### Default Behavior

Stop instances with the default IP (`172.31.34.141`):

```json
{}
```

### Override Target IP

Stop instances with a different `PrivateIP` tag:

```json
{
    "privateIp": "10.0.1.50"
}
```

### Dry Run

Validate permissions and logic without stopping:

```json
{
    "dryRun": true
}
```

### Combined

```json
{
    "privateIp": "10.0.1.50",
    "dryRun": true
}
```

---

## Response Format

### Success — Instances Stopped

```json
{
    "statusCode": 200,
    "StoppedInstances": [
        {
            "InstanceId": "i-0abcd1234efgh5678",
            "PreviousState": "running",
            "CurrentState": "stopping"
        }
    ],
    "DryRun": false
}
```

### Success — No Instances Found

```json
{
    "statusCode": 200,
    "StoppedInstances": [],
    "message": "No instances found matching criteria"
}
```

### Success — Dry Run

```json
{
    "statusCode": 200,
    "DryRun": true,
    "WouldStop": ["i-0abcd1234efgh5678"]
}
```

### Error — API Failure

```json
{
    "statusCode": 500,
    "error": "An error occurred...",
    "StoppedInstances": []
}
```

---

## Monitoring

Logs are emitted to **Amazon CloudWatch Logs** under the Lambda function's log group. Key log messages:

| Log Level | Message | Meaning |
|-----------|---------|---------|
| `INFO` | `Looking for instances with tag PrivateIP=...` | Search started |
| `INFO` | `Found instance i-... (state: running)` | Match found |
| `INFO` | `Skipping i-... (already stopped)` | Instance already stopped |
| `INFO` | `Stopping instances: [...]` | Stop command issued |
| `INFO` | `Instance i-...: running -> stopping` | State transition logged |
| `ERROR` | `Failed to describe instances: ...` | API call failed |
| `ERROR` | `Failed to stop instances: ...` | Stop command failed |

---

## License

MIT License — feel free to use and modify as needed.
"""

with open("/mnt/agents/output/README.md", "w") as f:
    f.write(readme_content)

print("README.md saved successfully!")
