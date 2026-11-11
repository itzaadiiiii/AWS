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
