terraform {
  backend "s3" {
    region         = "eu-central-1"
    bucket         = "cubicl-terraform-state-production"
    dynamodb_table = "terraform-lock"
    key            = "terraform.tfstate"
  }

}

provider "aws" {
  region  = "eu-central-1"
}

resource "aws_s3_bucket" "lambda_bucket" {
  bucket = "slack-bot-lambda-bucket"
}

resource "aws_s3_bucket_acl" "lambda_bucket_acl" {
  bucket = aws_s3_bucket.lambda_bucket.id
  acl    = "private"
}

resource "aws_s3_object" "lambda_slack_bot" {
  bucket = aws_s3_bucket.lambda_bucket.id

  key    = "slack_bot.zip"
  source = "../slack_bot.zip"

  etag = filemd5("../slack_bot.zip")
}

resource "aws_lambda_function" "slack_bot" {
  function_name = "coffee-break-slack-bot"

  s3_bucket = aws_s3_bucket.lambda_bucket.id
  s3_key    = aws_s3_object.lambda_slack_bot.key

  runtime = "python3.9"
  handler = "app.handler"
  timeout = 60 # in seconds

  source_code_hash = filebase64sha256("../slack_bot.zip")

  role = aws_iam_role.lambda_exec.arn

  environment {
    variables = {
      SLACK_TOKEN = data.aws_secretsmanager_secret_version.slack_token.secret_string
      USERS = data.aws_secretsmanager_secret_version.users.secret_string
    }
  }
}

resource "aws_lambda_function_event_invoke_config" "this" {
  function_name          = aws_lambda_function.slack_bot.function_name
  maximum_retry_attempts = 0
}

resource "aws_cloudwatch_event_rule" "cloudwatch_scheduled_event" {
  name                = "cloudwatch-scheduled-event"
  description         = "Fires every monday at 11am"
  schedule_expression = "cron(0 9 ? * MON *)"
}

resource "aws_cloudwatch_event_target" "slack_bot_trigger" {
  rule      = aws_cloudwatch_event_rule.cloudwatch_scheduled_event.name
  target_id = "slack-bot-lambda"
  arn       = aws_lambda_function.slack_bot.arn
}

resource "aws_cloudwatch_log_group" "slack_bot" {
  name = "/aws/lambda/${aws_lambda_function.slack_bot.function_name}"

  retention_in_days = 30
}

resource "aws_lambda_permission" "allow_cloudwatch" {
  statement_id  = "AllowExecutionFromCloudWatch"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.slack_bot.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.cloudwatch_scheduled_event.arn
}


resource "aws_iam_role" "lambda_exec" {
  name = "serverless_lambda"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Sid    = ""
      Principal = {
        Service = "lambda.amazonaws.com"
      }
      }
    ]
  })
}

resource "aws_iam_policy" "ssm_policy" {
  name        = "SecretsmanagerReadPolicy"
  description = "Secretsmanager read policy"

  policy = <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Action": [
        "secretsmanager:GetSecretValue*"
      ],
      "Effect": "Allow",
      "Resource": "*"
    }
  ]
}
EOF
}

resource "aws_iam_role_policy_attachment" "ssm_policy" {
  role       = aws_iam_role.lambda_exec.name
  policy_arn = aws_iam_policy.ssm_policy.arn
}

resource "aws_iam_role_policy_attachment" "lambda_policy" {
  role       = aws_iam_role.lambda_exec.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}