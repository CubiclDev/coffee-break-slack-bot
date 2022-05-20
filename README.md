# Coffee Break Slackbot

This bot invites randomly picked pairs to a coffee break in Slack each week.
As a result, the exchange in the team is increased.

## Requirements
- [Python 3.9](https://www.python.org/)
- [jq](https://stedolan.github.io/jq/manual/)
- [Terraform 1.0.8](https://www.terraform.io/)

## Setup

### Terraform Backend
Create a [Terraform S3 Backend](https://www.terraform.io/language/settings/backends/s3) in the AWS account.

### Slack App
Create an app in the [Slack app directory](https://api.slack.com/apps?new_app=1).
Select `From an app manifest` and choose the workspace for the app.
Copy the content of the `manifest.yml` file into the `YAML` field and create the app.
Then go to the  `OAuth & Permissions` section and install the app to your workspace.

If you like you can give your bot a profile picture.

### Configure Lambda Environment Variables
Create a secret named `coffee-break-slack-bot/key` in the AWS SecretsManager which obtains the Slack app token.
You can find the token in the `OAuth & Permissions` section of your app.

You also need to configure the user list in the SecretsManager. 
Create a secret named `coffee-break-slack-bot/users` to store the user list.
You can find the id of a slack member in the profile information. Press `More` and copy the member id.
The format of the list has to be `["U1", "U2", ...]`.

## Testing
Install requirements before running test
```shell
pip install -r requirements-dev.txt
```

## Deployment
To run terraform apply, first create a session with the AWS Account.

If you use a role run the following command:
```shell
aws_credentials=$(aws sts assume-role --profile PROFILE_NAME --role-arn ROLE_ARN --role-session-name "RoleSession" --serial-number MFA_SERIAL_NUMBER --token-code MFA_TOKEN)
```

If you use your user run the following command:
```shell
aws_credentials=$(aws sts get-session-token --profile PROFILE_NAME --serial-number MFA_SERIAL_NUMBER --token-code MFA_TOKEN)
```

After that export the following variables:
```shell
export AWS_ACCESS_KEY_ID=$(echo $aws_credentials|jq '.Credentials.AccessKeyId'|tr -d '"')
export AWS_SECRET_ACCESS_KEY=$(echo $aws_credentials|jq '.Credentials.SecretAccessKey'|tr -d '"')
export AWS_SESSION_TOKEN=$(echo $aws_credentials|jq '.Credentials.SessionToken'|tr -d '"')
```

Before you run `terraform apply` make sure that you have installed the dependencies for the lambda function:
```shell
bash scripts/build.sh
```

Navigate to the infrastructure directory, initialize terraform backend and deploy.
```shell
cd infrastructure
terraform init
terraform apply
```

## Useful terraform commands
```shell
init # initialize terraform backend for selected folder
fmt # format terraform files in this folder
validate # validate the syntax
plan # create plan
apply # create, approve and deploy plan
```
