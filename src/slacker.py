from botocore.vendored import requests
import json
import yaml

class SlackMessage():
    def __init__(self, success, validation_count, result_dict, err_details, function_name, aws_request_id, log_group_name, log_stream_name):
        if success and validation_count > 0:
            self.validation = "PASSED"
        elif success and validation_count == 0:
            self.validation = "NO RECORDS"
        else:
            self.validation = "FAILED"
        self.result_dict = result_dict
        self.err_details = err_details
        self.function_name = function_name
        self.aws_request_id = aws_request_id
        self.log_group_name = log_group_name
        self.log_stream_name = log_stream_name

    def send(self, logger, dest_url, extra_message=None):
        result_blocks = []
        for data_provider, dpdict in self.result_dict.items():
            result_blocks.append({
                'type': 'section',
                'text': {
                    'type': 'mrkdwn',
                    'text': '*Data Provider - {}*'.format(data_provider.upper())
                }
            })
            for message_type, result in dpdict.items():
                # Add count details
                result_blocks.append({
                    'type': 'section',
                    'text': {
                        'type': 'mrkdwn',
                        'text': (
                            '*{} messages*\n'.format(message_type.upper())+
                            '* {} records from {} files analyzed\n'.format(result['records_analyzed'], result['files_analyzed'])+
                            '* {}/{} validations failed ({}%)\n'.format(result['validations_failed'], result['validation_count'], result['validations_failed']*100/result['validation_count'])
                        )
                    }
                })
                # Add error information
                if result['validations_failed'] > 0:
                    errKey = data_provider+','+message_type
                    errors = yaml.dump(self.err_details[errKey], default_flow_style=False)
                    if errors:
                        groupErrors = "```%s```" % errors
                    if len(groupErrors) > 2947:
                        groupErrors = groupErrors[:2947] + " ... [TRUNCATED LIST]```"
                    result_blocks.append({
                                        "type": "section",
                                        "text": {
                                                "type": "mrkdwn",
                                                "text": "*Error Details*\n"+groupErrors
                                        }
                                    },)
            result_blocks.append({'type': 'divider'})

        alert_tags = ""
        if self.validation != "PASSED":
            alert_tags = "<@WAZT6U66R>"

        slack_message = {
            "blocks": [
                {
                    "type": "divider"
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "*=== Daily CVP Sandbox Ingestion Report ===*\n {}\n {}".format(self.validation, alert_tags)
                    }
                },
                {
                    "type": "divider"
                },
            ]+result_blocks+[
                {
                    "type": "section",
                    "text": {
                            "type": "mrkdwn",
                        "text": "*Function Name:* %s" % self.function_name
                    }
                },
                {
                    "type": "section",
                    "text": {
                            "type": "mrkdwn",
                        "text": "*Request ID:* %s" % self.aws_request_id
                    }
                },
                {
                    "type": "section",
                    "text": {
                            "type": "mrkdwn",
                        "text": "*CloudWatch Logs:* %s" % "https://console.aws.amazon.com/cloudwatch/home?region=us-east-1#logEventViewer:group="+self.log_group_name+";stream="+self.log_stream_name
                    }
                }
            ]
        }
        if extra_message:
            slack_message['blocks'].append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "*Additional Information:* %s" % extra_message
                }
            })
        slack_message['blocks'].append({"type": "divider"})
        logger.info("Sending slack message to %s" % dest_url)
        logger.debug(json.dumps(slack_message))
        with requests.Session() as session:
            r = session.post(dest_url, data=json.dumps(slack_message))
            logger.info("Slack API response: %s [%s] (%s)" % (
                r.status_code, r.reason, r.text))
