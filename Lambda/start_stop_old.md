# AWS Lambda EC2 Auto Stop Scheduler using Tags

## Project Overview

This project demonstrates how to automatically stop Amazon EC2 instances using **AWS Lambda**, **Amazon EventBridge (CloudWatch Events)**, and **EC2 Tags**.

Instead of hardcoding EC2 Instance IDs, the Lambda function dynamically discovers instances based on tags and stops them automatically.

This is a common production approach for reducing AWS costs by shutting down development, QA, or non-production instances outside business hours.

---

## Architecture

```
Amazon EventBridge (Schedule)
            │
            ▼
      AWS Lambda Function
            │
            ▼
Describe EC2 Instances by Tag
            │
            ▼
Stop Matching EC2 Instances
```

---

## Prerequisites

- AWS Account
- EC2 Instance(s)
- AWS Lambda
- Amazon EventBridge
- IAM Role with EC2 permissions
- Python 3.x Runtime

---

## Step 1: Tag Your EC2 Instances

Example:

| Key | Value |
|------|-------|
| AutoSchedule | true |

Only instances with this tag will be stopped.

---

## Step 2: Create IAM Role

Attach the following permissions to the Lambda execution role.

```json
{
    "Version":"2012-10-17",
    "Statement":[
        {
            "Effect":"Allow",
            "Action":[
                "ec2:DescribeInstances",
                "ec2:StopInstances"
            ],
            "Resource":"*"
        }
    ]
}
```

---

## Step 3: Lambda Code

```python
import boto3

ec2 = boto3.client("ec2")

def lambda_handler(event, context):

    response = ec2.describe_instances(
        Filters=[
            {
                "Name": "tag:AutoSchedule",
                "Values": ["true"]
            }
        ]
    )

    instance_ids = [
        instance["InstanceId"]
        for reservation in response["Reservations"]
        for instance in reservation["Instances"]
    ]

    if instance_ids:
        ec2.stop_instances(InstanceIds=instance_ids)

    return {
        "StoppedInstances": instance_ids
    }
```

---

## Step 4: Deploy Lambda

- Create Lambda Function
- Runtime: Python 3.13 (or latest supported)
- Paste the code
- Assign the IAM Role
- Deploy

---

## Step 5: Create EventBridge Schedule

Navigate to:

```
Amazon EventBridge
→ Rules
→ Create Rule
```

Example Schedule:

```
Every weekday at 7 PM

Cron Expression:

0 19 ? * MON-FRI *
```

Select your Lambda function as the target.

---

## How It Works

1. EventBridge triggers Lambda on schedule.
2. Lambda searches for EC2 instances with the tag:

```
AutoSchedule = true
```

1. Lambda collects matching Instance IDs.
2. Lambda stops all matching instances.
3. Returns the list of stopped instances.

---

## Example Tags

### Example 1

| Key | Value |
|------|-------|
| AutoSchedule | true |

---

### Example 2

| Key | Value |
|------|-------|
| Environment | Dev |

Filter:

```python
Filters=[
    {
        "Name":"tag:Environment",
        "Values":["Dev"]
    }
]
```

---

### Example 3

| Key | Value |
|------|-------|
| Project | Finance |

Filter:

```python
Filters=[
    {
        "Name":"tag:Project",
        "Values":["Finance"]
    }
]
```

---

### Example 4 (Multiple Tags)

```python
Filters=[
    {
        "Name":"tag:Environment",
        "Values":["Dev"]
    },
    {
        "Name":"tag:Application",
        "Values":["Backend"]
    }
]
```

Only instances matching **both** tags will be returned.

---

## Expected Output

```json
{
    "StoppedInstances": [
        "i-0123456789abcdef0",
        "i-0fedcba9876543210"
    ]
}
```

---

## Benefits

- No hardcoded Instance IDs
- Easily scalable
- Tag-based automation
- Cost optimization
- Production-friendly
- Easy to manage across multiple environments

---

## Use Cases

- Stop Development EC2 instances after office hours
- Stop QA environments overnight
- Weekend shutdown automation
- Cost optimization
- Scheduled maintenance windows

---

## Future Enhancements

- Start EC2 instances automatically in the morning
- Send SNS notifications after stopping instances
- Support multiple tag filters
- Exclude production instances
- Log actions to CloudWatch Logs
- Add email alerts for failures

---

## Author

**Aditya Patil**  
Cloud & DevOps Engineer
