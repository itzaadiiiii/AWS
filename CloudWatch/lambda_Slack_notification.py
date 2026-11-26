# Create a lambda function with Python environmnent and Paste this code.
# Create the slack webhook and To create Goto api.slack.com/apps -> Create app from scratch ---> Give name and select Workspace and Create app, Once created Goto --> Incoming Webhooks --> Activate incoming webhooks ---> Add New Webhook ---> (So while creating you need a Channel so Create Channel inside the Slack i.e. CloudWatch Alarms), now you can mention this channel and Create a webhook, Once created --> Copy the Webhook URL. 
# Create an envrironment variable inside lambda ---> Configuration ----> Environment variables ---> Add --->  SLACK_WEBHOOK_URL = "<paste webhook url>"
import json
import os
import urllib.request
import urllib.parse
from datetime import datetime, timezone

SLACK_WEBHOOK_URL = os.environ['SLACK_WEBHOOK_URL']

ALARM_CONFIG = {
    'ALARM': {
        'color': '#FF0000',
        'emoji': '🔴',
        'label': 'CRITICAL ALERT'
    },
    'OK': {
        'color': '#36A64F',
        'emoji': '✅',
        'label': 'RESOLVED'
    }
}


def get_region_from_arn(arn):
    # arn:aws:sns:us-east-1:123456789012:topic-name
    try:
        return arn.split(':')[3]
    except Exception:
        return 'us-east-1'


def format_timestamp(timestamp):
    try:
        dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        return dt.strftime('%Y-%m-%d %H:%M:%S UTC')
    except Exception:
        return timestamp


def build_slack_message(alarm):
    config = ALARM_CONFIG.get(alarm['state'], {
        'color': '#808080',
        'emoji': '❓',
        'label': f"UNKNOWN: {alarm['state']}"
    })

    alarm_link = (
        f"https://{alarm['region']}.console.aws.amazon.com/cloudwatch/home"
        f"?region={alarm['region']}#alarmsV2:alarm/{urllib.parse.quote(alarm['alarm_name'])}"
    )

    return {
        "attachments": [{
            "color": config['color'],
            "blocks": [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": f"{config['emoji']}  {config['label']}: {alarm['alarm_name']}",
                        "emoji": True
                    }
                },
                {
                    "type": "section",
                    "fields": [
                        {"type": "mrkdwn", "text": f"*Metric:*\n{alarm['namespace']} → {alarm['metric_name']}"},
                        {"type": "mrkdwn", "text": f"*State Change:*\n{alarm['previous_state']} → *{alarm['state']}*"},
                        {"type": "mrkdwn", "text": f"*Account ID:*\n`{alarm['account_id']}`"},
                        {"type": "mrkdwn", "text": f"*Time:*\n{format_timestamp(alarm['timestamp'])}"}
                    ]
                },
                {
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": f"*Description:*\n{alarm['description']}"}
                },
                {
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": f"*Reason:*\n{alarm['reason']}"}
                },
                {
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": f"<{alarm_link}|🔍 View Alarm in AWS Console>"}
                },
                {"type": "divider"},
                {
                    "type": "context",
                    "elements": [{"type": "mrkdwn", "text": f"🌍 Region: `{alarm['region']}` | 🏦 Account: `{alarm['account_id']}`"}]
                }
            ]
        }]
    }


def send_to_slack(payload):
    data = json.dumps(payload).encode('utf-8')
    req  = urllib.request.Request(
        SLACK_WEBHOOK_URL,
        data=data,
        headers={'Content-Type': 'application/json'},
        method='POST'
    )
    with urllib.request.urlopen(req, timeout=8) as response:
        return response.read()


def lambda_handler(event, context):
    print(f"Event received: {json.dumps(event)}")

    for record in event.get('Records', []):
        # Extract region from SNS topic ARN directly
        region = get_region_from_arn(record['Sns']['TopicArn'])

        message = json.loads(record['Sns']['Message'])

        alarm = {
            'alarm_name':     message.get('AlarmName', 'Unknown Alarm'),
            'description':    message.get('AlarmDescription', 'No description provided'),
            'state':          message.get('NewStateValue', 'UNKNOWN'),
            'previous_state': message.get('OldStateValue', 'UNKNOWN'),
            'reason':         message.get('NewStateReason', 'No reason provided'),
            'account_id':     message.get('AWSAccountId', 'Unknown'),
            'region':         region,
            'namespace':      message.get('Trigger', {}).get('Namespace', 'Unknown'),
            'metric_name':    message.get('Trigger', {}).get('MetricName', 'Unknown'),
            'timestamp':      message.get('StateChangeTime', datetime.now(timezone.utc).isoformat()),
        }

        print(f"Alarm: {alarm['alarm_name']} | State: {alarm['state']} | Region: {alarm['region']}")

        payload = build_slack_message(alarm)
        send_to_slack(payload)

        print(f"✅ Sent to Slack | Alarm: {alarm['alarm_name']} | State: {alarm['state']}")

    return {'statusCode': 200, 'body': 'OK'}
