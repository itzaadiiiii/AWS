# AWS Backup failure monitoring – 

# Requirement: Detect when scheduled backups fail for EC2, EBS, RDS or other supported resources.
# This is useful for disaster recovery and compliance.

# Trigger: AWS Backup → EventBridge → Lambda.




from common import send_notification


# AWS Backup job states that require investigation.
FAILED_STATES = [
    "FAILED",
    "ABORTED",
    "EXPIRED"
]


def lambda_handler(event, context):

    detail = event.get("detail", {})

    state = detail.get("state")

    # Ignore successful backup jobs.
    if state not in FAILED_STATES:

        return {
            "status": "ignored",
            "backup_state": state
        }

    backup_details = {

        "backup_job_id": detail.get("backupJobId"),

        "resource_arn": detail.get("resourceArn"),

        "resource_type": detail.get("resourceType"),

        "backup_vault": detail.get("backupVaultName"),

        "state": state,

        "status_message": detail.get("statusMessage"),

        "account": event.get("account"),

        "region": event.get("region"),

        "timestamp": event.get("time")

    }

    send_notification(
        "CRITICAL: AWS Backup Job Failed",
        backup_details
    )

    return {
        "status": "alert_sent",
        "backup_job": backup_details
    }



# Example notification:

    # AWS BACKUP FAILURE
    
    # Resource: RDS Production Database
    # Backup Job: backup-job-12345
    
    # State: FAILED
    
    # Region: ap-southeast-2
    
    # Action Required:
    # 1. Investigate backup failure.
    # 2. Check backup vault and IAM permissions.
    # 3. Verify available recovery points.
    # 4. Retry backup if required.
    # 5. Create Jira incident.


# This helps prevent situations where teams assume their backups are working without verifying actual backup job completion.

