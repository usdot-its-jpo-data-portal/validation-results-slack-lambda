import boto3
from copy import deepcopy
from datetime import datetime, timedelta
import json
import logging
import os
import pickle
import traceback
import yaml
from pysqs_extended_client.SQSClientExtended import SQSClientExtended

from slacker import SlackMessage


class ResultAggregator():
    def __init__(self, event, context, logger, env_var_dict):
        self.context = context
        self.logger = logger
        self.env_var_dict = env_var_dict
        self.report_done = False
        self.sqs_client = boto3.client('sqs')
        self.lambda_client = boto3.client('lambda')
        self.sqs_extended = SQSClientExtended()
        self.result_queue_url = self.sqs_client.get_queue_url(QueueName=env_var_dict['SQS_RESULT_QUEUE'])['QueueUrl']

        # init depending on if starting a new daily report or continuing the last report
        if event.get('report_date'):
            self.report_info = deepcopy(event)
            self.logger.info('Continuing report for {} ({} validations included)'.format(event.get('report_date'), event.get('total_validation_count')))
        else:
            self.report_info = {
                'is_local_test': False,
                'result_dict': {},
                'error_dict': {},
                'sqs_msgs_received': 0,
                'total_validation_count': 0,
                'total_validations_failed': 0,
                'received_message_ids': [],
                'report_date': (datetime.today() - timedelta(days=1)).strftime('%Y-%m-%d')
            }
            self.logger.info('Starting report for {}'.format(self.report_info.get('report_date')))

    def get_queue_attributes(self):
        queue_attrs = self.sqs_client.get_queue_attributes(
            QueueUrl=self.result_queue_url,
            AttributeNames=['ApproximateNumberOfMessages',
                            'ApproximateNumberOfMessagesNotVisible']
        )
        msgs_visible = queue_attrs['Attributes']['ApproximateNumberOfMessages']
        msgs_flight = queue_attrs['Attributes']['ApproximateNumberOfMessagesNotVisible']
        return msgs_visible, msgs_flight

    def decide_to_continue(self, messages):
        # check if need to trigger new lambda
        if self.context.get_remaining_time_in_millis() < 60000:
            self.logger.info("Less than one minute left: stopping process to trigger another lambda.")
            return False

        # check if any more messages
        msgs_visible, msgs_flight = self.get_queue_attributes()
        msg_total = int(msgs_visible) + int(msgs_flight)
        if msg_total == 0:
            self.report_done = True
            self.logger.info("Report done. No more messages left in queue.")
            return False

        # check date
        try:
            message = messages[0]
        except:
            self.logger.debug('DEBUG: Cannot get next message. Error details: {}'.format(str(traceback.format_exc())))
            return True

        message_sent_time = int(message['Attributes']['SentTimestamp'])
        message_sent_day = datetime.fromtimestamp(message_sent_time/1000).strftime('%Y-%m-%d')
        if message_sent_day > self.report_info['report_date']:
            self.report_done = True
            self.logger.info("Report done. All validations from {} have been aggregated".format(self.report_info['report_date']))
            return False

        return True

    def parse_message_body(self, cur_msg_json):
        cur_msg_key = cur_msg_json['key']
        self.logger.info("Analyzing file %s" % cur_msg_key)

        data_provider, message_type = cur_msg_json['data_group'].split(':')
        if not self.report_info['result_dict'].get(data_provider):
            self.report_info['result_dict'][data_provider] = {}
        if not self.report_info['result_dict'][data_provider].get(message_type):
            self.report_info['result_dict'][data_provider][message_type] = {
                'files_analyzed': 0,
                'records_analyzed': 0,
                'validation_count': 0,
                'validations_failed': 0
            }
        errKey = data_provider+','+message_type
        if not self.report_info['error_dict'].get(errKey):
            self.report_info['error_dict'][errKey] = {}

        self.report_info['result_dict'][data_provider][message_type]['files_analyzed'] += 1

        cur_msg_results = cur_msg_json['results']
        self.report_info['result_dict'][data_provider][message_type]['records_analyzed'] += cur_msg_results['num_records']
        self.report_info['result_dict'][data_provider][message_type]['validation_count'] += cur_msg_results['num_validations']
        self.report_info['result_dict'][data_provider][message_type]['validations_failed'] += cur_msg_results['num_validation_errors']
        self.report_info['total_validation_count'] += cur_msg_results['num_validations']
        self.report_info['total_validations_failed'] += cur_msg_results['num_validation_errors']
        if cur_msg_results['errors']:
            self.logger.debug("Found failed validation: %s" % cur_msg_results['errors'])
            for errFieldDetailStr, numRowswithError in cur_msg_results['errors'].items():
                if errFieldDetailStr not in self.report_info['error_dict'][errKey]:
                    self.report_info['error_dict'][errKey][errFieldDetailStr] = []
                errorStr = '{}: error in {}/{} records'.format(cur_msg_key, numRowswithError, cur_msg_results['num_records'])
                self.report_info['error_dict'][errKey][errFieldDetailStr].append(errorStr)

    def parse_message(self, message):
        self.report_info['sqs_msgs_received'] += 1
        self.logger.debug("Current message: %s" % message['MessageId'])
        if message['MessageId'] in self.report_info['received_message_ids']:
            self.logger.debug("Detected previously processed SQS message, skipping to prevent duplicates...")
            return
        self.report_info['received_message_ids'].append(message['MessageId'])
        cur_msg_json = json.loads(message['Body'])
        self.parse_message_body(cur_msg_json)

    def get_next_message(self, messages, last_receipt_handle=None):
        if last_receipt_handle:
            self.sqs_extended.delete_message(
                queue_url=self.result_queue_url, receipt_handle=last_receipt_handle)
        messages = self.sqs_extended.receive_message(
            queue_url=self.result_queue_url, max_number_Of_Messages=1)
        return messages

    def send_report(self):
        self.logger.debug(
            "Finished message polling loop, found %d SQS messages." % self.report_info['sqs_msgs_received'])
        self.logger.debug("Error details: %s" % json.dumps(self.report_info['error_dict']))
        slack_message = SlackMessage(
            success=self.report_info['total_validations_failed'] == 0,
            validation_count=self.report_info['total_validation_count'],
            result_dict=self.report_info['result_dict'],
            error_dict=self.report_info['error_dict'],
            function_name=self.context.function_name,
            aws_request_id=self.context.aws_request_id,
            log_group_name=self.context.log_group_name,
            log_stream_name=self.context.log_stream_name,
            recipients_dict=self.env_var_dict['RECIPIENTS_DICT'],
            sender=self.env_var_dict['SENDER'],
            cc=self.env_var_dict['CC'],
            report_date=self.report_info['report_date']
        )

        msgs_visible, msgs_flight = self.get_queue_attributes()
        seconds_remaining = self.context.get_remaining_time_in_millis()/1000
        queue_status_msg = "\nAnalysis reports waiting to be aggregated: *%s*\nAnalysis reports currently being aggregated: *%s*\nSeconds Remaining in Execution: *%s*" % (
            str(msgs_visible), str(msgs_flight), str(seconds_remaining))
        slack_message.send(self.logger, self.env_var_dict['SLACK_WEBHOOK'], extra_message=queue_status_msg)
        pass

    def trigger_lambda(self):
        # invoke lambda asynchronously to continue aggregating results for report
        response = self.lambda_client.invoke(
            FunctionName=self.context.function_name,
            InvocationType='Event',
            LogType='Tail',
            ClientContext='',
            Payload=json.dumps(self.report_info).encode('utf-8'),
        )
        self.logger.info(response)
        return

    def run(self):
        if self.report_info['is_local_test']:
            self.logger.info("(Local Test) Running as local test!")

        messages = self.sqs_extended.receive_message(queue_url=self.result_queue_url, max_number_Of_Messages=1)
        while self.decide_to_continue(messages):
            try:
                message = messages[0]
            except:
                self.logger.debug('DEBUG: Cannot get next message. Error details: {}'.format(str(traceback.format_exc())))
                messages = self.get_next_message(messages)
            self.parse_message(message)
            messages = self.get_next_message(messages, last_receipt_handle=message['ReceiptHandle'])

        if self.report_done:
            self.send_report()
        else:
            self.trigger_lambda()


if __name__ == '__main__':
    context = type('obj', (object,), {
        'function_name': 'local_validation_results_function',
        'aws_request_id': 'local_aws_request_id_12345',
        'log_group_name': 'local_log_group_name_abcde',
        'log_stream_name': 'log_stream_name'})
    result_aggregator = ResultAggregator(context, logger)
    result_aggregator.run()
