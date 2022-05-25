# thaw.py
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
import json
from botocore import exceptions
from configparser import ConfigParser

# Import utility helpers
sys.path.insert(1, os.path.realpath(os.path.pardir))
import helpers

# Get configuration
CONFIG_FILE = '/home/ec2-user/mpcs-cc/gas/util/thaw/thaw_config.ini'
config = ConfigParser()
config.read_file(open(CONFIG_FILE))

s3 = boto3.client('s3')
dynamodb = boto3.client('dynamodb')
sqs = boto3.client('sqs')
glacier = boto3.client('glacier')

# Add utility code here
def main(): 
    print('... checking for files to thaw ...')
    while True: 
        response, receipt_handle = receive_message()
        if response == None: 
            continue
        message_dict = json.loads(response['Message'])
        if message_dict['StatusCode'] != 'Succeeded': 
            print('Error: 500 - StatusCode was not <Succeeded>')
            continue
        JobId = message_dict['JobId']
        ArchiveId = message_dict['ArchiveId']
        
        body_bytes = get_job_output(JobId)
        
        s3_key_result_file, job_id = generate_s3_key_name(ArchiveId)
        if s3_key_result_file == None: 
            print('Error: 500 - Server Error')
            continue
        
        if upload_to_s3(body_bytes, s3_key_result_file) == None: 
            continue
        
        if update_dynamodb(s3_key_result_file, job_id) == None: 
            continue
        
        delete_message(receipt_handle)

def receive_message(): 
        response = sqs.receive_message(
            QueueUrl=config.get('aws', 'SQSThawQueueUrl'), 
            MaxNumberOfMessages=1, 
            WaitTimeSeconds=20)
        try:  # Receive message
            message = response['Messages'][0]
            message_body = message['Body']
            receipt_handle = message['ReceiptHandle']
        except KeyError: # No messages in queue
            return None, None
        return ast.literal_eval(message_body), receipt_handle

def get_job_output(JobId): 
    response = glacier.get_job_output(
        vaultName=config.get('aws', 'S3GlacierBucketName'),
        jobId=JobId)
    return response['body'].read()

def generate_s3_key_name(ArchiveId): 
    response = dynamodb.scan(
        TableName=config.get('aws', 'DynamoDBTable'), 
        Select='SPECIFIC_ATTRIBUTES', 
        ProjectionExpression="user_id, job_id, input_file_name, results_file_archive_id", 
        FilterExpression='results_file_archive_id = :id', 
        ExpressionAttributeValues={":id": {"S": ArchiveId}} # Would love to get exclusive start_key working
    )
    if len(response['Items']) == 1: 
        job = response['Items'][0]
        object_prefix = config.get('aws', 'S3ObjectPrefix')
        user_id = job['user_id']['S']
        job_id = job['job_id']['S']
        input_file_name = job['input_file_name']['S']
        results_file_suffix = input_file_name.rstrip('.vcf') + '.annot.vcf'
        s3_key_result_file = f'{object_prefix}/{user_id}/{job_id}~{results_file_suffix}'
        return s3_key_result_file, job_id
    elif len(response['Items']) == 0: 
        print('Error: 404 - Item not found')
    elif len(response['Items']) > 1: 
        print('Error: 500 - Server Error')
    return None, None

def upload_to_s3(body_bytes, s3_key_result_file): 
    try: 
        response = s3.put_object(
            Body=body_bytes, 
            Bucket=config.get('aws', 'ResultsBucket'), 
            Key=s3_key_result_file
        )
        return response
    except boto3.exceptions.S3UploadFailedError as e: # 
        # print(e.__class__.__name__)
        code = e.response['Error']['Code']
        print({
            'code': 500, 
            'status': 'Server Error', 
            'message': f'S3UploadFailedError: {e}',
        })
        return None

def update_dynamodb(s3_key_result_file, job_id):
    try: # Update dynamodb with Glacier Archive Id                 
        response = dynamodb.update_item(
            TableName=config.get('aws', 'DynamoDBTable'), 
            Key={'job_id': {'S': job_id}}, 
            ExpressionAttributeValues={
                ':f': {'S': s3_key_result_file}
            }, 
            UpdateExpression='SET s3_key_result_file = :f REMOVE results_file_archive_id'
        )
        return response
    except exceptions.ClientError as e: # Error - Table does not exist
        code = e.response['Error']['Code']
        if code == 'ResourceNotFoundexception': 
            print({
                'code': 404, 
                'status': 'Not Found', 
                'message': f'ResourceNotFoundException: {e}'
            })
            return None
        else: 
            print({
                'code': 500, 
                'status': 'Server Error', 
                'message': f'{e}'
            })
            return None
    
def delete_message(receipt_handle): 
    try: # Delete message from SQS queue
        response = sqs.delete_message(
            QueueUrl=config.get('aws', 'SQSThawQueueUrl'), 
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
### EOF