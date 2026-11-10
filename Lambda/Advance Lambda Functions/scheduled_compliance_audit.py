import boto3

from common import send_notification


s3 = boto3.client("s3")

ec2 = boto3.client("ec2")


def lambda_handler(event, context):

    findings = []

    # ------------------------------------------------
    # 1. S3 BUCKET SECURITY CHECK
    # ------------------------------------------------

    buckets = s3.list_buckets()["Buckets"]

    for bucket in buckets:

        bucket_name = bucket["Name"]

        # Check S3 public access configuration.
        try:

            pab = s3.get_public_access_block(
                Bucket=bucket_name
            )["PublicAccessBlockConfiguration"]

            if not all([
                pab.get("BlockPublicAcls", False),
                pab.get("IgnorePublicAcls", False),
                pab.get("BlockPublicPolicy", False),
                pab.get("RestrictPublicBuckets", False)
            ]):

                findings.append({
                    "resource": bucket_name,
                    "issue": "S3 Public Access Block is incomplete"
                })

        except s3.exceptions.NoSuchPublicAccessBlockConfiguration:

            findings.append({
                "resource": bucket_name,
                "issue": "S3 Public Access Block is missing"
            })

        # Check default encryption configuration.
        try:

            s3.get_bucket_encryption(
                Bucket=bucket_name
            )

        except s3.exceptions.ServerSideEncryptionConfigurationNotFoundError:

            findings.append({
                "resource": bucket_name,
                "issue": "Default encryption configuration missing"
            })

    # ------------------------------------------------
    # 2. EBS ENCRYPTION CHECK
    # ------------------------------------------------

    paginator = ec2.get_paginator("describe_volumes")

    for page in paginator.paginate():

        for volume in page["Volumes"]:

            if not volume.get("Encrypted", False):

                findings.append({

                    "resource": volume["VolumeId"],

                    "issue": "EBS volume is not encrypted",

                    "size": volume["Size"]

                })

    # ------------------------------------------------
    # 3. SECURITY GROUP CHECK
    # ------------------------------------------------

    sensitive_ports = [22, 3389, 3306, 5432, 1433]

    groups = ec2.describe_security_groups()["SecurityGroups"]

    for group in groups:

        for rule in group["IpPermissions"]:

            protocol = rule.get("IpProtocol")

            start = rule.get("FromPort")

            end = rule.get("ToPort")

            sensitive = (
                protocol == "-1"
                or (
                    start is not None
                    and end is not None
                    and any(start <= p <= end for p in sensitive_ports)
                )
            )

            if not sensitive:
                continue

            for ip_range in rule.get("IpRanges", []):

                if ip_range.get("CidrIp") == "0.0.0.0/0":

                    findings.append({

                        "resource": group["GroupId"],

                        "issue": "Sensitive port open to public internet",

                        "port": f"{start}-{end}"

                    })

    # ------------------------------------------------
    # 4. SEND COMPLIANCE REPORT
    # ------------------------------------------------

    if findings:

        send_notification(
            "Daily AWS Security Compliance Report",
            {
                "total_findings": len(findings),
                "findings": findings
            }
        )

    return {
        "total_findings": len(findings),
        "findings": findings
    }
