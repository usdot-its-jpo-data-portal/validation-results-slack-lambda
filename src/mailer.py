import boto3
from botocore.exceptions import ClientError


CHARSET = "UTF-8"


class EmailReport():
    def __init__(self, sender):
        self.client = boto3.client('ses')
        self.sender = sender

    def send(self, logger, recipients, cc, subject, body):
        bodyhtml = """<html>
        <head></head>
        <body>
        <p>{}</p>
        </body>
        </html>
        """.format(body.replace("\n", '<br/>'))

        try:
            #Provide the contents of the email.
            response = self.client.send_email(
                Destination={
                    'ToAddresses': recipients,
                    'CcAddresses': cc
                },
                Message={
                    'Body': {
                        'Html': {
                            'Charset': CHARSET,
                            'Data': bodyhtml,
                        },
                        'Text': {
                            'Charset': CHARSET,
                            'Data': body,
                        },
                    },
                    'Subject': {
                        'Charset': CHARSET,
                        'Data': subject,
                    },
                },
                Source=self.sender,
                # If you are not using a configuration set, comment or delete the
                # following line
                # ConfigurationSetName=CONFIGURATION_SET,
            )
        # Display an error if something goes wrong.
        except ClientError as e:
            logger.debug(e.response['Error']['Message'])
            raise e
        else:
            logger.info("Email sent! Message ID:"),
            logger.info(response['MessageId'])
