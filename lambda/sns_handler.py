import json
import boto3
import os

ses = boto3.client('ses', region_name=os.environ['AWS_REGION'])

def lambda_handler(event, context):
    for record in event['Records']:
        sns_message = json.loads(record['Sns']['Message'])
        
        if sns_message.get('action') == 'user_created':
            send_welcome_email(sns_message.get('user_id'))
        
    return {'statusCode': 200, 'body': json.dumps('Notification processed')}

def send_welcome_email(user_id):
    ses.send_email(
        Source=os.environ['SES_FROM_EMAIL'],
        Destination={'ToAddresses': ['admin@example.com']},
        Message={
            'Subject': {'Data': 'New User Registration'},
            'Body': {'Text': {'Data': f'New user registered with ID: {user_id}'}}
        }
    )
