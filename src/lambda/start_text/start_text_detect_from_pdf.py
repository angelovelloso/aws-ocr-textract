import urllib
import boto3
import os
import logging

logger = logging.getLogger()
textract = boto3.client('textract')
s3 = boto3.client('s3')

sns_topic_arn = os.environ["SNS_TOPIC_ARN"]
sns_role_arn = os.environ["SNS_ROLE_ARN"]

def handler(event, context):
	source_bucket = event['Records'][0]['s3']['bucket']['name']
	object_key = urllib.parse.unquote_plus(
					event['Records'][0]['s3']['object']['key'])

	textract_result = textract.start_document_text_detection(
		DocumentLocation={
			"S3Object": {
				"Bucket": source_bucket,
				"Name": object_key
			}
		},
		NotificationChannel={
			"SNSTopicArn": sns_topic_arn,
			"RoleArn": sns_role_arn
		}
	)

	logger.info(f'Objeto S3: {object_key}')
	logger.info(f'Resultado chamada: {textract_result}')