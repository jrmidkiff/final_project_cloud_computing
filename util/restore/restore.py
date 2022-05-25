# restore.py
#
# NOTE: This file lives on the Utils instance
#
# Copyright (C) 2011-2019 Vas Vasiliadis
# University of Chicago
##
__author__ = 'Vas Vasiliadis <vas@uchicago.edu>'

import os
import sys

# Import utility helpers
sys.path.insert(1, os.path.realpath(os.path.pardir))
import helpers

# Get configuration
CONFIG_FILE = '/home/ec2-user/mpcs-cc/gas/util/archive/restore_config.ini'
config = ConfigParser()
config.read_file(open(CONFIG_FILE))
glacier = boto3.client('glacier')

# Add utility code here
def main(): 
    while True: 
        print('... checking for users to thaw ...')
        response = sqs.receive_message(
            QueueUrl=config.get('aws', 'SQSRestoreQueueUrl'), 
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
        except KeyError: 
            print(f'KeyError!')
            continue
        print(f"Received request to restore all of {user_id}'s files")
        archive_ids = get_archive_ids(user_id)
        for id in archive_ids: 
            initiate_job()
        
        try: # Delete message from SQS queue
            response = sqs.delete_message(
                QueueUrl=config.get('aws', 'SQSRestoreQueueUrl'), 
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
            continue 

def get_archive_ids(user_id): 
    try: 
        response = dynamodb.query(
            TableName=config.get('aws', 'DynamoDBTable'), 
            IndexName=config.get('aws', 'DynamoDBIndex'),
            Select='SPECIFIC_ATTRIBUTES', 
            ProjectionExpression="results_file_archive_id", 
            KeyConditionExpression="user_id = :u", 
            ExpressionAttributeValues={
                ":u": {"S": user_id}}, 
            FilterExpression='attribute_not_exists(s3_key_result_file) and attribute_exists(results_file_archive_id)' 
        )
        return response['Items']
    except ClientError as e: 
        print(e)
        return []

def initiate_job(id, tier='Expedited'): 
    try: 
        response = glacier.initiate_job( # Initiate job to retrieve from glacier
            vaultName=config.get('aws', 'S3GlacierBucketName'), 
            jobParameters={
                Type='archive-retrieval',
                ArchiveId=id, 
                SNSTopic=config.get('aws', 'SNSThawTopicARN'), 
                Tier=tier, 
                Outputlocation={
                    'S3': {
                        'BucketName': config.get('aws', 'ResultsBucket')
                    }
                }
            }
        )
        print(f"    initiating {tier} job with jobId {response['jobId']}")
    except glacier.exceptions.InsufficientCapacityException or glacier.exceptions.InsufficientCapacityException: 
        initiate_job(id, tier='Standard')        


if __name__ == '__main__': 
    main()