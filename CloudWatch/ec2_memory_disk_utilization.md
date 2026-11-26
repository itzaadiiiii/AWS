# Steps:
## 1) Create role with SSM & CLoudWatch Full Access
## 2) Create a parameter in Systems Manager with the name "/alarm/AWS-CWAgentLinConfig" and store the value.
## 3) Create instance, Attach above role and Paste the below code in Userdata Script while Launching Instance: 

```bash
#!/bin/bash
wget https://s3.amazonaws.com/amazoncloudwatch-agent/linux/amd64/latest/AmazonCloudWatchAgent.zip
unzip AmazonCloudWatchAgent.zip
sudo ./install.sh
sudo /opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-ctl -a fetch-config -m ec2 -c ssm:/alarm/AWS-CWAgentLinConfig -s

```

### What It Does

This `userdata.sh` script runs when an Amazon EC2 Linux instance launches to install and start the **Amazon CloudWatch Agent** using a configuration stored in AWS Systems Manager (SSM) Parameter Store:

* Downloads the latest Linux `amd64` CloudWatch Agent `.zip` bundle from AWS S3
* Extracts the archive and runs `install.sh` with `sudo` to install the agent binary and service
* Runs `amazon-cloudwatch-agent-ctl` in EC2 mode (`-m ec2`) to fetch the JSON configuration from SSM Parameter Store (`/alarm/AWS-CWAgentLinConfig`), apply it (`fetch-config`), and start the agent (`-s`), typically for collecting OS-level telemetry like memory and disk metrics referenced in `memory_disk.json`

To verify it is running on an instance, check 
```
sudo /opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-ctl -m ec2 -a status
```
(or )
```
systemctl status amazon-cloudwatch-agent.service
```
 And confirm metrics appear under the `CWAgent` namespace in CloudWatch.

### Easier Ways Than the 3-Year-Old `wget`/`unzip` Pattern

Downloading and unzipping `AmazonCloudWatchAgent.zip` in user data still works, but it has drawbacks: you have to manage `wget`/`unzip` availability, re-download on every launch, and handle user-data failures manually. Depending on how you launch and manage instances, these approaches are cleaner:

* **AWS Systems Manager (SSM) Distributor & Run Command:** For existing EC2 instances or fleet rollouts, install and update the `AmazonCloudWatchAgent` package centrally via SSM Distributor rather than embedding a `wget`/`unzip` script in user data.
* **Bake into a Golden AMI:** Pre-install the agent (and even bake a default config) into your custom Amazon Machine Image using Packer or EC2 Image Builder so new instances start faster without pulling from S3 on boot.
* **CloudWatch Console / Workload Detection:** For guided setup on EC2 instances, use the CloudWatch console workflow to generate and apply agent configurations without manually writing shell download steps.
* **Infrastructure as Code (Terraform / CloudFormation):** Keep the same `amazon-cloudwatch-agent-ctl -a fetch-config ... -s` command if using user data, or pass a template/SSM parameter reference cleanly in your launch template so config changes don't require rewriting shell scripts.
