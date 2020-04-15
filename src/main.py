import json
import logging
import os

from aggregator import ResultAggregator


env_var_tuples = [
    ('SQS_RESULT_QUEUE', None, True),
    ('SLACK_WEBHOOK', None, True),
    ('RECIPIENTS_DICT', '{}', True),
    ('SENDER', None, False),
    ('CC', '', True),
    ('VERBOSE_OUTPUT', False, False)
]
env_var_dict = {}

for env_var_name, env_var_default, required in env_var_tuples:
    env_var_dict[env_var_name] = os.environ.get(env_var_name, env_var_default)
    if required:
        assert env_var_dict[env_var_name] != None, "Failed to get required environment variable {}".format(env_var_name)

# Mailer properties
env_var_dict['RECIPIENTS_DICT'] = json.loads(env_var_dict['RECIPIENTS_DICT'])
env_var_dict['CC'] = [i.strip() for i in env_var_dict['CC'].split(',')]

# Setup logger
VERBOSE_OUTPUT = True if env_var_dict['VERBOSE_OUTPUT'] == 'TRUE' else False
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
    result_aggregator = ResultAggregator(event, context, logger, env_var_dict)
    result_aggregator.run()


if __name__ == '__main__':
    context = type('obj', (object,), {
        'function_name': 'local_validation_results_function',
        'aws_request_id': 'local_aws_request_id_12345',
        'log_group_name': 'local_log_group_name_abcde',
        'log_stream_name': 'log_stream_name',
        })
    event = {'is_local_test': True}
    result_aggregator = ResultAggregator(event, context, logger, env_var_dict)
    result_aggregator.run()
