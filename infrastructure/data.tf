data "archive_file" "this" {
  output_path = "${path.module}/../slack_bot.zip"
  source_dir = "${path.module}/../slack_bot_with_dependencies"
  type        = "zip"
}

data "aws_secretsmanager_secret" "slack_token" {
  name = "coffee-break-slack-bot/key"
}

data "aws_secretsmanager_secret_version" "slack_token" {
  secret_id = data.aws_secretsmanager_secret.slack_token.id
}

data "aws_secretsmanager_secret" "users" {
  name = "coffee-break-slack-bot/users"
}

data "aws_secretsmanager_secret_version" "users" {
  secret_id = data.aws_secretsmanager_secret.users.id
}
