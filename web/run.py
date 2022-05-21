# run.py
#
# Copyright (C) 2011-2019 Vas Vasiliadis
# University of Chicago
#
# Wrapper script for running AnnTools
#
##
__author__ = 'Vas Vasiliadis <vas@uchicago.edu>'

import sys
import time
import driver
import boto3
import os
import re
import shutil
from botocore import exceptions

"""A rudimentary timer for coarse-grained profiling
"""
class Timer(object):
    def __init__(self, verbose=True):
        self.verbose = verbose

    def __enter__(self):
        self.start = time.time()
        return self

    def __exit__(self, *args):
        self.end = time.time()
        self.secs = self.end - self.start
        if self.verbose:
            print(f"Approximate runtime: {self.secs:.2f} seconds")

def main(arg): 
    with Timer():
        user_bad, job_id, file_name = arg.split('~')
        dot, user = user_bad.split('/')
        print(f'user: {user}')
        print(f'job_id: {job_id}')
        print(f'file_name: {file_name}')

        try: 
            driver.run(arg, 'vcf')
        except FileNotFoundError: 
            print({
                'code': 404, 
                'status': 'NotFound', 
                'message': f'FileNotFoundError: {arg}',
            })
            return None
        s3 = boto3.client('s3')
        
        d = {}
        print('are we here?')
        for x in os.listdir('/home/ec2-user/mpcs-cc'): 
            if x.startswith(f'{user}~{job_id}'): 
                if x.endswith('.annot.vcf') or x.endswith('.count.log'): 
                    _, _2, relevant_file = x.split('~')
                    file_key = f'jmidkiff/{user}/{job_id}~{relevant_file}'
                    if x.endswith('.annot.vcf'): 
                        d['result_file'] = file_key
                    else: 
                        d['log_file'] = file_key
                    try: 
                        s3.upload_file(
                            Filename=x, 
                            Bucket='mpcs-cc-gas-results', 
                            Key=file_key
                        )
                    except boto3.exceptions.S3UploadFailedError as e: # 
                        # print(e.__class__.__name__)
                        code = e.response['Error']['Code']
                        print({
                            'code': 500, 
                            'status': 'Server Error', 
                            'message': f'S3UploadFailedError: {e}',
                        })
                        return None
                    except FileNotFoundError: 
                        print({
                            'code': 404, 
                            'status': 'NotFound', 
                            'message': f'FileNotFoundError: {file_key}',
                        })
                        return None
                    except Exception as e: 
                        print(e) 
                        return None
                # Best error catching may occur here by looking at the stdout.txt 
                # and if there's an error in there, then updating DynamoDB
                # Or perhaps stderr.txt, and raising Errors. 
                os.remove(x)   
                
        dynamodb = boto3.client('dynamodb')
        try: 
            dynamodb.update_item(
                TableName='jmidkiff_annotations', 
                Key={
                    'job_id': {
                        'S': job_id
                    }
                }, 
                ExpressionAttributeValues={
                    ':cp': {'S': 'COMPLETED'}, 
                    ':re': {'S': d['result_file']}, 
                    ':log': {'S': d['log_file']}, 
                    ':tim': {'N': str(time.time())}
                }, 
                UpdateExpression='SET job_status = :cp, s3_key_result_file = :re, s3_key_log_file = :log, complete_time = :tim'
            )
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
        except KeyError as e: # Error - Missing Results or Log File
            print({
                'code': 500, 
                'status': 'Server Error', 
                'message': f'Results File or Log File are missing: {e}'
            })
            return None
            
if __name__ == '__main__':
    # Call the AnnTools pipeline
    if len(sys.argv) > 1:
        main(sys.argv[1])
        
    else:
        print("A valid .vcf file must be provided as input to this program.")

### EOF