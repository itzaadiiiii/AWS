# ACM certificate expiration monitoring - 

# Requirement: Identify certificates that are approaching expiration.
# For example, notify the DevOps team 30 days before an imported certificate expires.

import boto3

from datetime import datetime, timezone

from common import send_notification


acm = boto3.client("acm")


def lambda_handler(event, context):

    # Notify when certificate expires within 30 days.
    threshold_days = 30

    now = datetime.now(timezone.utc)

    findings = []

    paginator = acm.get_paginator("list_certificates")

    for page in paginator.paginate(
        CertificateStatuses=["ISSUED"]
    ):

        for certificate in page["CertificateSummaryList"]:

            arn = certificate["CertificateArn"]

            # Retrieve certificate details.
            details = acm.describe_certificate(
                CertificateArn=arn
            )["Certificate"]

            expiry = details.get("NotAfter")

            if not expiry:
                continue

            remaining_days = (expiry - now).days

            if remaining_days <= threshold_days:

                findings.append({

                    "domain": details.get("DomainName"),

                    "certificate_arn": arn,

                    "expiry_date": expiry.isoformat(),

                    "remaining_days": remaining_days,

                    "type": details.get("Type"),

                    "renewal_status": details.get(
                        "RenewalSummary", {}
                    ).get("RenewalStatus")

                })

    if findings:

        send_notification(
            "AWS ACM Certificate Expiration Alert",
            {
                "total_certificates": len(findings),
                "certificates": findings
            }
        )

    return {
        "total_findings": len(findings),
        "findings": findings
    }

# Enterprise use case:
#     - Monitor imported certificates.
#     - Monitor certificates requiring manual renewal.
#     - Notify owners before expiration.
#     - Create Jira tickets for renewal.
#     - Validate certificates used by ALB, CloudFront and other supported services.

# Note: ACM automatically renews eligible Amazon-issued certificates when renewal requirements are met. This Lambda is mainly useful for additional monitoring and certificates that need manual intervention.
