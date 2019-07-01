# validation-results-slack-lambda

A Python AWS Lambda function designed to poll SQS for validation result messages, aggregate the errors into a packaged message, and send it to a Slack channel.

Designed for use in conjunction with the [DataHub Canary Lambda function](https://github.com/usdot-its-jpo-data-portal/canary-lambda).

## Requirements
- Python 3.7 (virtualenv recommended)
- pip3
- SQS Queue with messages matching correct schema (see details below)
  - (If using larger messages) S3 storage bucket for hosting large SQS messages
- Slack channel webhook

## Configuration

| Property         | Description                                                                              |
| ---------------- | ---------------------------------------------------------------------------------------- |
| SQS_RESULT_QUEUE | SQS queue name (not URL or ARN, just the name) from which validation results will arrive |
| SLACK_WEBHOOK    | Slack channel webhook to which messages will be sent                                     |
| VERBOSE_OUTPUT   | Set to `TRUE` to activate, all other falues will set this to false                       |

## Installation and Running

### Local Installation

Local installation only requires you to run `pip install -r requirements.txt`.

After that you may simply run the function by setting the environment variables and running `python main.py`.

### AWS Lambda Installation

1. Create a new Lambda function with runtime `Python 3.7`
2. Give the lambda function appropriate permissions
  - `s3:Get*` for your S3/SQS storage bucket
  - `s3:List*` for your S3/SQS storage bucket
  - `sqs:*` for your SQS queue
3. Run `package.sh` locally which will create `results.zip`
4. Upload the `results.zip` as the Lambda function code
5. Add a CloudWatch CRON event to trigger the function periodically
6. Set the environment variables

## Acknowledgements

SQS Extended Library Code sourced from https://github.com/timothymugayi/boto3-sqs-extended-client-lib
