# validation-results-slack-lambda

This is a Python project designed for us as an Amazon Web Services (AWS) Lambda function. It is set up to poll SQS for validation result messages, aggregate the errors into a packaged message, and send it to a Slack channel.

Designed for use in conjunction with the [DataHub Canary Lambda function](https://github.com/usdot-its-jpo-data-portal/canary-lambda).

## Getting Started

Since this code is designed to run in AWS, you will need an AWS account. Additionally you will need an SQS queue to which results are pushed (see the [DataHub Canary Lambda function](https://github.com/usdot-its-jpo-data-portal/canary-lambda)), and lastly a Slack webhook to which this function can send messages.

### Prerequisites

- Python 3.7 ([virtualenv](https://virtualenv.pypa.io/en/latest/) recommended when running locally)
- [pip3](https://pip.pypa.io/en/stable/)
- [SQS Queue](https://aws.amazon.com/sqs/) with messages matching correct schema (see details below)
  - (If using larger messages) S3 storage bucket for hosting large SQS messages
- [Slack channel webhook](https://api.slack.com/messaging/webhooks)

### Configuration

The following table lists the environment variables used for configuration.

| Property         | Description                                                                              |
| ---------------- | ---------------------------------------------------------------------------------------- |
| SQS_RESULT_QUEUE | SQS queue name (not URL or ARN, just the name) from which validation results will arrive |
| SLACK_WEBHOOK    | Slack channel webhook to which messages will be sent                                     |
| VERBOSE_OUTPUT   | Set to `TRUE` to activate, all other falues will set this to false                       |
| RECIPIENTS_DICT  | Stringified JSON object with data provider names as the keys and arrays of email         |
|                  | addresses as the values                                                                  |
| SENDER           | Email address from which to send the aggregated count and validation report              |
| CC               | Comma delimited email addresses that the email report will be Cc'ed to                   |

### Installing and Running Locally

While the function works best as a Lambda function, you may also test it locally. You will still need to set up the aformentioned SQS queue and Slack webhook.

We recommend you use [virtualenv](https://virtualenv.pypa.io/en/latest/).

Note that you will also need to have an AWS profile set up, see [instructions here](https://docs.aws.amazon.com/cli/latest/userguide/cli-chap-configure.html).

To install and run the function, follow the following steps:

1. `pip install -r requirements.txt`
2. `python main.py`

## Deployment

To deploy this as an AWS Lambda function:

1. Create a new Lambda function with runtime `Python 3.7`
2. Give the lambda function appropriate permissions
  - `s3:Get*` for your S3/SQS storage bucket
  - `s3:List*` for your S3/SQS storage bucket
  - `sqs:*` for your SQS queue
  - `ses:*` for permission to send email through AWS SES.
3. Run `package.sh` locally which will create `results.zip`
4. Upload the `results.zip` as the Lambda function code
5. Add a CloudWatch CRON event to trigger the function periodically
6. Set the environment variables

## Contributing

Please use GitHub pull requests and issues to contribute to this project and report problems.

## Authors

The ITS DataHub development team.

## License

This project is licensed under the Apache License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

SQS Extended Library Code sourced from https://github.com/timothymugayi/boto3-sqs-extended-client-lib

## Code.gov Registration Info

Agency: DOT

Short Description: A Python AWS Lambda function designed to poll SQS for validation result messages, aggregate the errors into a packaged message, and send it to a Slack channel.

Status: Released

Tags: connected, vehicles, transportation, python, aws, lambda

Labor hours: 0

Contact Name: Brian Brotsos

Contact Phone: (202) 366-3000
