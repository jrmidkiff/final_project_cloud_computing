# archive.py
#
# NOTE: This file lives on the Utils instance
#
# Copyright (C) 2011-2019 Vas Vasiliadis
# University of Chicago
##
__author__ = 'Vas Vasiliadis <vas@uchicago.edu>'

import os
import sys
import boto3
import ast
from botocore import exceptions
from configparser import ConfigParser

# Import utility helpers
sys.path.insert(1, os.path.realpath(os.path.pardir))
import helpers

# Get configuration
CONFIG_FILE = '/home/ec2-user/mpcs-cc/gas/util/archive/archive_config.ini'
config = ConfigParser()
config.read_file(open(CONFIG_FILE))

s3 = boto3.client('s3')
dynamodb = boto3.client('dynamodb')
sqs = boto3.client('sqs')
glacier = boto3.client('glacier')

# Add utility code here
def main(): 
    print('... checking for files to move to glacier ...')
    while True: 
        # Messages will not appear in this queue if the user was premium_user
        # at the time of job running, see run.py
        # But they do need to be deleted if the user upgraded within 5 minute interval
        response = sqs.receive_message(
            QueueUrl=config.get('aws', 'SQSArchiveQueueUrl'), 
            MaxNumberOfMessages=1, 
            WaitTimeSeconds=20)
        try:  # Receive message
            message = response['Messages'][0]
            message_body = message['Body']
            receipt_handle = message['ReceiptHandle']
        except KeyError: # No messages in queue
            continue
        actual_message = ast.literal_eval(message_body)
        try: 
            user_id = actual_message['user_id']
            job_id = actual_message['job_id']
            s3_key_result_file = actual_message['s3_key_result_file']
        except KeyError: 
            continue
                
        _, _, _, _, role, _, _ = helpers.get_user_profile(id=user_id) # Shitty utility return value
        if role == 'premium_user': 
            delete_message(receipt_handle)
            continue

        try: # Get S3 results file
            response = s3.get_object(
                Bucket=config.get('aws', 'ResultsBucket'),
                Key=s3_key_result_file)
            obj = response['Body'].read()
        except exceptions.ClientError as e: 
            print(f"{e}\nBucket:{config.get('aws', 'ResultsBucket')}\nKey:{s3_key_result_file}")
            continue
        
        # https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/glacier.html#Glacier.Client.upload_archive
        response = glacier.upload_archive(
            vaultName=config.get('aws', 'S3GlacierBucketName'),
            body = obj)
        location, archive_id = response['location'], response['archiveId']
        
        try: # Update dynamodb with Glacier Archive Id                 
            dynamodb.update_item(
                TableName=config.get('aws', 'DynamoDBTable'), 
                Key={'job_id': {'S': job_id}}, 
                ExpressionAttributeValues={
                    ':id': {'S': archive_id}
                }, 
                UpdateExpression='SET results_file_archive_id = :id REMOVE s3_key_result_file'
            )
        except exceptions.ClientError as e: # Error - Table does not exist
            code = e.response['Error']['Code']
            if code == 'ResourceNotFoundexception': 
                print({
                    'code': 404, 
                    'status': 'Not Found', 
                    'message': f'ResourceNotFoundException: {e}'
                })
                continue
            else: 
                print({
                    'code': 500, 
                    'status': 'Server Error', 
                    'message': f'{e}'
                })
                continue
        
        try: # Remove results file from S3
            s3.delete_object(
                Bucket=config.get('aws', 'ResultsBucket'),
                Key=s3_key_result_file)
        except exceptions.ClientError as e: 
            print(f"{e}\nBucket:{config.get('aws', 'ResultsBucket')}\nKey:{s3_key_result_file}")
            continue
        
        delete_message(receipt_handle)

def delete_message(receipt_handle): 
    try: # Delete message from SQS queue
        response = sqs.delete_message(
            QueueUrl=config.get('aws', 'SQSArchiveQueueUrl'), 
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
    main()
    # ### EOF