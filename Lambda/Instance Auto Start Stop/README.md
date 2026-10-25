I've written a Lambda function and a SAM template that deploys it with the schedules. I read "67 pm" as 6 or 7 PM and defaulted to 7 PM, so change `StopCron` if you meant 6.

**What it does**
- `lambda_function.py` takes `{"action": "stop"}` or `{"action": "start"}`. It finds instances tagged `Environment` = `Dev`, `QA` or `Stage`, stops the running ones or starts the stopped ones, and retries individually if a batch fails.
- It skips ASG-managed instances, spot instances, and anything tagged `SchedulerSkip=true`.
- It raises an error if any instance fails, so the CloudWatch alarm fires.
- `template.yaml` creates the function and a least-privilege IAM role. The role limits start/stop to resources with those `Environment` tags.
- It also creates two EventBridge Scheduler schedules (stop at 19:00 and start at 09:00, Monday to Friday) and an error alarm.
- Schedules use EventBridge Scheduler, not classic EventBridge rules, because Scheduler supports a `Timezone` parameter. You don't need to convert cron to UTC or handle DST yourself.

**Deploy**
```bash
cd ec2-scheduler
sam deploy --guided --parameter-overrides Timezone=<your IANA TZ> 
```
The default timezone is UTC, so set `Timezone` to your own.

**Alternatives to a custom Lambda**
- **Instance Scheduler on AWS** is the official AWS solution. It is tag-driven (`Schedule=office-hours`), handles multiple accounts and regions, and also covers RDS. It is the better choice if you want schedules managed as config, with different hours per tag value. The cost is a bigger CloudFormation stack with its own Lambda, DynamoDB table and so on.
- **EventBridge Scheduler universal target** calls `ec2:StartInstances` and `ec2:StopInstances` directly with no Lambda. It needs explicit instance IDs, so it doesn't work for tag-based selection unless you maintain the ID list.
- **SSM Automation** with `AWS-StopEC2Instance` and `AWS-StartEC2Instance`, run from a Maintenance Window or State Manager association, can target by tag. It is more setup than the Lambda for the same result.
- **Auto Scaling scheduled actions** (min/max/desired = 0 at night) are the right approach if the Dev, QA and Stage instances sit in ASGs. That is why the Lambda skips ASG members.

**Things to check**
- Instances with instance-store volumes lose that data on stop. Check your Dev, QA and Stage workloads for this.
- If an instance has an Elastic IP, it keeps it across stop and start. Otherwise the public IP changes, so make sure DNS or allowlists don't depend on it.
- Stopped instances still bill for EBS. If the instances are in a different region from where you deploy, deploy the stack in that region, because the Lambda uses its own region.
- Apps that need to come up in order after the 9 AM start, such as a DB before the app tier, should get a delay or a second schedule.
