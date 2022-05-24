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

# Import utility helpers
sys.path.insert(1, os.path.realpath(os.path.pardir))
import helpers

# Get configuration
CONFIG_FILE = '/home/ec2-user/mpcs-cc/gas/util/archive/archive_config.ini'
s3 = boto3.client('s3')
dynamodb = boto3.client('dynamodb')
sqs = boto3.client('sqs')
config = ConfigParser()
config.read_file(open(CONFIG_FILE))

# Add utility code here
# sqs.receive_message here

s3.copy(
    CopySource={
        'Bucket': config.get('aws', 'ResultsBucket'), 
        'Key': ''
    }, 
    Bucket=config.get('aws', 'S3GlacierBucketName'), 
    Key='')
### EOF