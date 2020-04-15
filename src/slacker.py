import requests
import json
import yaml
import markdown

from mailer import EmailReport


class SlackMessage():
    def __init__(self, success, validation_count, result_dict, err_details,
    function_name, aws_request_id, log_group_name, log_stream_name,
    recipients_dict=None, sender=None, cc=[]):
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
        if not sender:
            self.emailReport = None
        else:
            self.emailReport = EmailReport(sender)
        self.recipients_dict = recipients_dict
        self.cc = cc


    def send(self, logger, dest_url, extra_message=None):
        ## TODO: refactor basic report aggregation to aggregator
        result_tuples = []
        for data_provider, dpdict in self.result_dict.items():
            result_tuples.append(('section', 'mrkdwn', '**Data Provider - {}**\n'.format(data_provider.upper())))
            # email_text = '*Data Provider - {}*\n'.format(data_provider.upper())
            for message_type, result in dpdict.items():
                # Add count details
                result_tuples.append(('section', 'mrkdwn', '**{} messages**\n'.format(message_type.upper())))
                text = '- {} records from {} files analyzed\n'.format(result['records_analyzed'], result['files_analyzed'])
                if result['validation_count'] < result['records_analyzed']:
                    text += '- Schema validation is not currently done for {} from {}\n'.format(message_type.upper(), data_provider.upper())
                else:
                    text += '- {}/{} validations failed ({}%)\n'.format(result['validations_failed'], result['validation_count'], result['validations_failed']*100/result['validation_count'])
                result_tuples.append(('section', 'mrkdwn', text))
                # email_text += text
                # Add error information
                if result['validations_failed'] > 0:
                    errKey = data_provider+','+message_type
                    errors = yaml.dump(self.err_details[errKey], default_flow_style=False)
                    if errors:
                        groupErrors = "```%s```" % errors
                    if len(groupErrors) > 2947:
                        groupErrors = groupErrors[:2947] + " ... [TRUNCATED LIST]```"
                    result_tuples.append(('section', 'mrkdwn', "**Error Details**\n"+groupErrors+"\n"))
            result_tuples.append(('divider', None, None))

            if self.emailReport and self.recipients_dict.get(data_provider):
                recipients = self.recipients_dict.get(data_provider)
                logger.info('Emailing {} report to: {}'.format(data_provider, ','.join(recipients)))
                self.emailReport.send(logger, recipients, self.cc,
                subject='Daily CVP Sandbox Ingestion Report for {}'.format(data_provider.upper()),
                body="\n".join([textText for blockType, textType, textText in result_tuples if textText]),
                bodyHtml=" ".join([markdown.markdown(textText) for blockType, textType, textText in result_tuples if textText]))

        alert_tags = ""
        if self.validation != "PASSED":
            alert_tags = "<@WAZT6U66R>"

        result_tuples = [
            ('divider', None, None),
            ('section', 'mrkdwn', "**=== Daily CVP Sandbox Ingestion Report ===**\n {}\n {}".format(self.validation, alert_tags)),
            ('divider', None, None)
        ] + result_tuples + [
            ('section', 'mrkdwn', "**Function Name:** %s" % self.function_name),
            ('section', 'mrkdwn', "**Request ID:** %s" % self.aws_request_id),
            ('section', 'mrkdwn', "**CloudWatch Logs:** %s" % "https://console.aws.amazon.com/cloudwatch/home?region=us-east-1#logEventViewer:group="+self.log_group_name+";stream="+self.log_stream_name)
        ]
        if extra_message:
            result_tuples.append(('section', 'mrkdwn', "**Additional Information:** %s" % extra_message))

        slack_message = {
            "blocks": [{'type': blockType, 'text': {'type': textType, 'text': textText}} if blockType != 'divider'
                        else {'type': 'divider'}
                        for blockType, textType, textText in result_tuples]+[{"type": "divider"}]
        }

        logger.info("Sending slack message to %s" % dest_url)
        logger.debug(json.dumps(slack_message))
        with requests.Session() as session:
            r = session.post(dest_url, data=json.dumps(slack_message))
            logger.info("Slack API response: %s [%s] (%s)" % (
                r.status_code, r.reason, r.text))
