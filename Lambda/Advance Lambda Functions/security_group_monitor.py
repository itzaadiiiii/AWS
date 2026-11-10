# Security group modification monitoring – 

# Requirement: Detect when someone changes security group rules, particularly when they expose sensitive ports publicly.

# Trigger: CloudTrail → EventBridge → Lambda.

import boto3

from common import send_notification


ec2 = boto3.client("ec2")


# Ports that require additional security review.
SENSITIVE_PORTS = [
    22,      # SSH
    3389,    # RDP
    3306,    # MySQL
    5432,    # PostgreSQL
    1433,    # SQL Server
    27017    # MongoDB
]


def lambda_handler(event, context):

    detail = event.get("detail", {})

    event_name = detail.get("eventName")

    request = detail.get("requestParameters", {})

    # Identify the affected security group.
    group_id = request.get("groupId")

    if not group_id:

        print("Security group ID not found in event")

        return

    # Retrieve current security group configuration.
    response = ec2.describe_security_groups(
        GroupIds=[group_id]
    )

    findings = []

    for group in response["SecurityGroups"]:

        for rule in group["IpPermissions"]:

            protocol = rule.get("IpProtocol")

            from_port = rule.get("FromPort")

            to_port = rule.get("ToPort")

            # Identify sensitive ports or unrestricted protocols.
            sensitive = (
                protocol == "-1"
                or (
                    from_port is not None
                    and to_port is not None
                    and any(
                        from_port <= port <= to_port
                        for port in SENSITIVE_PORTS
                    )
                )
            )

            if not sensitive:
                continue

            public_cidrs = []

            for ip_range in rule.get("IpRanges", []):

                if ip_range.get("CidrIp") == "0.0.0.0/0":

                    public_cidrs.append("0.0.0.0/0")

            for ip_range in rule.get("Ipv6Ranges", []):

                if ip_range.get("CidrIpv6") == "::/0":

                    public_cidrs.append("::/0")

            if public_cidrs:

                findings.append({

                    "security_group": group_id,

                    "group_name": group["GroupName"],

                    "event": event_name,

                    "protocol": protocol,

                    "from_port": from_port,

                    "to_port": to_port,

                    "public_access": public_cidrs,

                    "actor": detail.get("userIdentity")

                })

    if findings:

        send_notification(
            "CRITICAL: Security Group Modification",
            {
                "findings": findings,
                "action": (
                    "Investigate the change and revoke unauthorized "
                    "public access through an approved remediation workflow."
                )
            }
        )

    return {
        "findings": findings
    }


# EventBridge event pattern:

# {
#   "source": ["aws.ec2"],
#   "detail-type": ["AWS API Call via CloudTrail"],
#   "detail": {
#     "eventSource": ["ec2.amazonaws.com"],
#     "eventName": [
#       "AuthorizeSecurityGroupIngress",
#       "AuthorizeSecurityGroupEgress",
#       "ModifySecurityGroupRules",
#       "RevokeSecurityGroupIngress",
#       "RevokeSecurityGroupEgress"
#     ]
#   }
# }

# This checks the current security group configuration. For a full before/after audit, also inspect CloudTrail request parameters and AWS Config configuration history.
