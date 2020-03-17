import boto3
import json
import logging
import os
import pickle
import yaml
from pysqs_extended_client.SQSClientExtended import SQSClientExtended

from slacker import SlackMessage

# SQS settings
SQS_RESULT_QUEUE = os.environ.get('SQS_RESULT_QUEUE')
assert SQS_RESULT_QUEUE != None, "Failed to get required environment variable SQS_RESULT_QUEUE"

# Slack properties
SLACK_WEBHOOK = os.environ.get('SLACK_WEBHOOK')
assert SLACK_WEBHOOK != None, "Failed to get required environment variable SLACK_WEBHOOK"

# Mailer properties
RECIPIENTS_DICT = json.loads(os.environ.get('RECIPIENTS_DICT', '{}'))
SENDER = os.environ.get('SENDER')
CC = os.environ.get('CC', '')
CC = [i.strip() for i in CC.split(',')]

# Setup logger
VERBOSE_OUTPUT = True if os.environ.get('VERBOSE_OUTPUT') == 'TRUE' else False
root = logging.getLogger()
if root.handlers:  # Remove default AWS Lambda logging configuration
    for handler in root.handlers:
        root.removeHandler(handler)
logger = logging.getLogger('canary')
logging.basicConfig(format='%(levelname)s %(message)s')
if VERBOSE_OUTPUT:
    logger.setLevel(logging.DEBUG)
else:
    logger.setLevel(logging.INFO)


def lambda_handler(event, context):
    aggregate_results(False, context=context)


def aggregate_results(local_test, context=None):
    if local_test:
        logger.info("(Local Test) Running as local test!")

    sqs_client = boto3.client('sqs')
    result_queue_url = sqs_client.get_queue_url(
        QueueName=SQS_RESULT_QUEUE)['QueueUrl']
    sqs_extended = SQSClientExtended.SQSClientExtended()

    # Prevent duplicating messages by tracking their IDs
    received_message_ids = []

    error_dict = {}
    result_dict = {}
    sqs_msgs_received = 0
    total_validation_count = 0
    total_validations_failed = 0

    messages = sqs_extended.receive_message(
        queue_url=result_queue_url, max_number_Of_Messages=1)
    error_details = {}
    while messages != None and len(messages) > 0 and context.get_remaining_time_in_millis() > 10000:
        sqs_msgs_received += 1
        logger.debug("Current message: %s" % messages[0]['MessageId'])
        if messages[0]['MessageId'] in received_message_ids:
            logger.debug(
                "Detected previously processed SQS message, skipping to prevent duplicates...")
        else:
            received_message_ids.append(messages[0]['MessageId'])
            cur_msg_json = json.loads(messages[0]['Body'])
            cur_msg_key = cur_msg_json['key']
            logger.info("Analyzing file %s" % cur_msg_key)

            data_provider, message_type = cur_msg_json['data_group'].split(':')
            if not result_dict.get(data_provider):
                result_dict[data_provider] = {}
            if not result_dict[data_provider].get(message_type):
                result_dict[data_provider][message_type] = {
                    'files_analyzed': 0,
                    'records_analyzed': 0,
                    'validation_count': 0,
                    'validations_failed': 0
                }
            errKey = data_provider+','+message_type
            if not error_dict.get(errKey):
                error_dict[errKey] = {}
                error_details[errKey] = {}
            error_dict[errKey][cur_msg_key] = []
            error_details[errKey][cur_msg_key] = []

            result_dict[data_provider][message_type]['files_analyzed'] += 1

            cur_msg_results = cur_msg_json['results']
            for result in cur_msg_results:
                result_dict[data_provider][message_type]['records_analyzed'] += 1
                for validation in result['Validations']:
                    result_dict[data_provider][message_type]['validation_count'] += 1
                    total_validation_count += 1
                    if not validation['Valid']:
                        result_dict[data_provider][message_type]['validations_failed'] += 1
                        total_validations_failed += 1
                        logger.debug("Found failed validation: %s" %
                                     validation)
                        error_dict[errKey][cur_msg_key].append(validation['Details'])
                        error_details[errKey][cur_msg_key].append(validation['Details'])

        sqs_extended.delete_message(
            queue_url=result_queue_url, receipt_handle=messages[0]['ReceiptHandle'])
        messages = sqs_extended.receive_message(
            queue_url=result_queue_url, max_number_Of_Messages=1)

    logger.debug(
        "Finished message polling loop, found %d SQS messages." % sqs_msgs_received)
    logger.debug("Error dict: %s" % json.dumps(error_dict))
    logger.debug("Error details: %s" % json.dumps(error_details))
    slack_message = SlackMessage(
        success= total_validations_failed == 0,
        validation_count=total_validation_count,
        result_dict=result_dict,
        err_details=error_details,
        function_name=context.function_name,
        aws_request_id=context.aws_request_id,
        log_group_name=context.log_group_name,
        log_stream_name=context.log_stream_name,
        recipients_dict=RECIPIENTS_DICT,
        sender=SENDER,
        cc=CC
    )

    queue_attrs = sqs_client.get_queue_attributes(
        QueueUrl=result_queue_url,
        AttributeNames=['ApproximateNumberOfMessages',
                        'ApproximateNumberOfMessagesNotVisible']
    )
    msgs_visible = queue_attrs['Attributes']['ApproximateNumberOfMessages']
    msgs_flight = queue_attrs['Attributes']['ApproximateNumberOfMessagesNotVisible']
    seconds_remaining = context.get_remaining_time_in_millis()/1000
    queue_status_msg = "\nAnalysis reports waiting to be aggregated: *%s*\nAnalysis reports currently being aggregated: *%s*\nSeconds Remaining in Execution: *%s*" % (
        str(msgs_visible), str(msgs_flight), str(seconds_remaining))
    slack_message.send(logger, SLACK_WEBHOOK, extra_message=queue_status_msg)


if __name__ == '__main__':
    context = type('obj', (object,), {
        'function_name': 'local_validation_results_function',
        'aws_request_id': 'local_aws_request_id_12345',
        'log_group_name': 'local_log_group_name_abcde',
        'log_stream_name': 'log_stream_name'})
    aggregate_results(True, context=context)
