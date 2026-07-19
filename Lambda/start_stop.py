import boto3
import logging
from botocore.exceptions import ClientError

logger = logging.getLogger()
logger.setLevel(logging.INFO)

ec2 = boto3.client("ec2")


def lambda_handler(event, context):
    """
    Stops EC2 instances filtered by the 'PrivateIP' tag.
    
    Expected event format (optional):
    {
        "dryRun": false,          # Set to true to validate without stopping
        "privateIp": "172.31.34.141"  # Override the default IP
    }
    """
    # --- Configuration ---
    # Allow IP override via event, fallback to default
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