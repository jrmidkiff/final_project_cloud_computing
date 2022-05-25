import boto3
import os
import uuid
import re
import subprocess
import ast
from botocore import exceptions
from configparser import ConfigParser

CONFIG_FILE = '/home/ec2-user/mpcs-cc/gas/ann/ann_config.ini'
s3 = boto3.client('s3')
dynamodb = boto3.client('dynamodb')
sqs = boto3.client('sqs')

def request_annotations():
    config = ConfigParser()
    config.read_file(open(CONFIG_FILE))
    
    queue_name = config.get('AWS', 'SQSRequestsQueueName')
    queue_name_dlq = config.get('AWS', 'SQSRequestsDLQQueueName')
    try: 
        url = sqs.get_queue_url(QueueName=queue_name)['QueueUrl']
        url_dql = sqs.get_queue_url(QueueName=queue_name_dlq)['QueueUrl']
        # print(f'url: {url}')
    except exceptions.ClientError as e: # Queue Not Found
        code = e.response['Error']['Code']
        if code == 'QueueDoesNotExist': 
            print({
                'code': 500, 
                'status': 'Queue Does Not Exist', 
                'message': f'Queue <{queue_name}> does not exist.'
            })
        else:
            print({
                'code': 500, 
                'status': 'Server Error', 
                'message': f'An error occurred: {e}'
            })  

    print('... checking for messages ...')
    while True: # Continuous loop for checking for messages
        response = sqs.receive_message(
            QueueUrl=url, AttributeNames=['All'], MaxNumberOfMessages=1, 
            WaitTimeSeconds=20, VisibilityTimeout=30)
        try: 
            message = response['Messages'][0]
            message_body = message['Body']
            receipt_handle = message['ReceiptHandle']
        except KeyError: # No messages in queue
            continue
        # https://favtutor.com/blogs/string-to-dict-python
        actual_message = ast.literal_eval(ast.literal_eval(message_body)['Message'])
        try: # Error - Posting doesn't contain either user_id or job_id, etc.
            user_id = actual_message['user_id']['S']
            job_id = actual_message['job_id']['S']
            input_file_name = actual_message['input_file_name']['S']
            s3_inputs_bucket = actual_message['s3_inputs_bucket']['S']
            s3_key_input_file = actual_message['s3_key_input_file']['S']
            user_email = actual_message['user_email']['S']
            new_folders = f'{user_id}/{job_id}'
            print(f'    received {new_folders}')
        except KeyError: 
            print({
                'code': 400, 
                'status': 'Bad Request', 
                'message': f'Message does not contain information needed.'
            })

        # Get the input file S3 object and copy it to a local file
        # Dont create directory for each result just append the job to file with ~ separator. Please do update when submitting your next assignment
        try: # Error - Job already exists in S3
            prefix = f"{config.get('AWS', 'Owner')}/{new_folders}/"
            response = s3.list_objects_v2(
                Bucket=config.get('AWS', 'ResultsBucket'), 
                Prefix=prefix)
            response['Contents']
            print({
                'code': 400, 
                'status': 'Bad Request', 
                'message': f'Job {job_id}/{input_file_name} already analyzed. Action halted to avoid duplication.'
            })
        except KeyError: 
            pass
            
        try: # Download S3 file
            new_file = f"{user_id}~{job_id}~{input_file_name}"
            response = s3.download_file(
                Bucket=s3_inputs_bucket, 
                Key=s3_key_input_file, 
                Filename=f"./{new_file}") # New HW5
        except exceptions.ClientError as e: # Error - File Not Found
            code = e.response['Error']['Code']
            if code == '404':
                print({
                    'code': 404, 
                    'status': 'Not Found', 
                    'message': f'<{s3_key_input_file}> not found.'
                })
            else: 
                print({
                    'code': 500, 
                    'status': 'Server Error', 
                    'message': f'An error occurred: {e}',
                })
        # https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/dynamodb.html#DynamoDB.Client.update_item
        # https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/Expressions.UpdateExpressions.html#Expressions.UpdateExpressions.SET
        try: # Update DynamoDB Record
            dynamodb.update_item(
                TableName=config.get('AWS', 'DynamoDBTable'), 
                Key={
                    'job_id': {
                        'S': job_id
                    }
                }, 
                ExpressionAttributeValues={
                    ':ru': {'S': 'RUNNING'}, 
                    ':pe': {'S': 'PENDING'}
                }, 
                UpdateExpression='SET job_status = :ru', 
                ConditionExpression='job_status = :pe'
            )
        except exceptions.ClientError as e: # Error - Job status not pending
            code = e.response['Error']['Code']
            if code == 'ConditionalCheckFailedException': 
                print({
                    'code': 500, 
                    'status': 'Server Error', 
                    'message': f'Job status was not <PENDING>.',
                })
            else: 
                print({
                    'code': 500, 
                    'status': 'Server Error', 
                    'message': f'An error occurred: {e}',
                })   
        # https://stackoverflow.com/a/4617069/8527838
        with open(f'./{user_id}~{job_id}~stdout.txt', 'w') as std_out, open(f'./{user_id}~{job_id}~stderr.txt', 'w') as std_err: 
            proc = subprocess.Popen(
                ['python', f'./run.py', f"./{new_file}", user_email], 
                stdout=std_out, stderr=std_err)
        try: # Delete message from SQS queue
            response = sqs.delete_message(
                QueueUrl=url, 
                ReceiptHandle=receipt_handle)
        except exceptions.ClientError as e: 
            code = e.response['Error']['Code']
            if code == 'ReceiptHandleIsInvalid': 
                print({
                    'code': 500, 
                    'status': 'Server Error', 
                    'message': f'Receipt Handle Is Invalid: {e}',
                }) 
            else: 
                print({
                    'code': 500, 
                    'status': 'Server Error', 
                    'message': f'An error occurred: {e}',
                })   



if __name__ == '__main__': 
    print('... Receiving from queue ...')
    request_annotations()