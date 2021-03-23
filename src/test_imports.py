import os

from unittest import TestCase, mock


TEST_ENV_VAR = {
    "SQS_RESULT_QUEUE": "",
    "SLACK_WEBHOOK": ""
}

class TestImports(TestCase):

    @mock.patch.dict(os.environ, TEST_ENV_VAR)
    def test_import_main(self):
        print('Test import main.py')
        import main

    def test_import_aggregator(self):
        print('Test impoart aggregator.py')
        import aggregator

    def test_import_mailer(self):
        print('Test import mailer.py')
        import mailer

    def test_import_slacker(self):
        print('Test import slacker.py')
        import slacker