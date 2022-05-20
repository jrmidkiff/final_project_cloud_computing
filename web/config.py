# config.py
#
# Copyright (C) 2011-2020 Vas Vasiliadis
# University of Chicago
#
# Set GAS configuration options based on environment
#
##
__author__ = 'Vas Vasiliadis <vas@uchicago.edu>'

import os
import json
import boto3
import base64
from botocore.exceptions import ClientError

basedir = os.path.abspath(os.path.dirname(__file__))

class Config(object):
  GAS_LOG_LEVEL = os.environ['GAS_LOG_LEVEL'] \
    if ('GAS_LOG_LEVEL' in os.environ) else 'INFO'
  GAS_LOG_FILE_PATH = basedir + (os.environ['GAS_LOG_FILE_PATH'] \
    if ('GAS_LOG_FILE_PATH' in os.environ) else "/log")
  GAS_LOG_FILE_NAME = os.environ['GAS_LOG_FILE_NAME'] \
    if ('GAS_LOG_FILE_NAME' in os.environ) else "gas.log"

  WSGI_SERVER = 'werkzeug'
  CSRF_ENABLED = True

  GAS_HOST_IP = os.environ['GAS_HOST_IP']
  GAS_HOST_PORT = int(os.environ['GAS_HOST_PORT'])
  GAS_APP_HOST = os.environ['GAS_APP_HOST']
  GAS_SERVER_NAME = f"{os.environ['GAS_HOST_IP']}:{os.environ['GAS_HOST_PORT']}"

  AWS_PROFILE_NAME = os.environ['AWS_PROFILE_NAME'] \
    if ('AWS_PROFILE_NAME' in  os.environ) else None
  AWS_REGION_NAME = os.environ['AWS_REGION_NAME'] \
    if ('AWS_REGION_NAME' in  os.environ) else "us-east-1"

  # Get various credentials from AWS Secrets Manager
  asm = boto3.client('secretsmanager', region_name=AWS_REGION_NAME)

  # Get Flask application secret
  try:
    asm_response = asm.get_secret_value(SecretId='gas/web_server')
    flask_secret = json.loads(asm_response['SecretString'])
  except ClientError as e:
    print(f"Unable to retrieve Flask secret from ASM: {e}")
    raise e
  SECRET_KEY = flask_secret['flask_secret_key']

  # Get RDS secret and construct database URI
  try:
    asm_response = asm.get_secret_value(SecretId='rds/accounts_database')
    rds_secret = json.loads(asm_response['SecretString'])
  except ClientError as e:
    print(f"Unable to retrieve accounts database credentials from ASM: {e}")
    raise e

  SQLALCHEMY_DATABASE_TABLE = os.environ['ACCOUNTS_DATABASE_TABLE']
  SQLALCHEMY_DATABASE_URI = "postgresql://" + \
    rds_secret['username'] + ':' + rds_secret['password'] + \
    '@' + rds_secret['host'] + ':' + str(rds_secret['port']) + \
    '/' + SQLALCHEMY_DATABASE_TABLE
  SQLALCHEMY_TRACK_MODIFICATIONS = True

  # Get the Globus Auth client ID and secret
  try:
    asm_response = asm.get_secret_value(SecretId='globus/auth_client')
    globus_auth = json.loads(asm_response['SecretString'])
  except ClientError as e:
    print(f"Unable to retrieve Globus Auth credentials from ASM: {e}")
    raise e

  # Set the Globus Auth client ID and secret
  GAS_CLIENT_ID = globus_auth['gas_client_id']
  GAS_CLIENT_SECRET = globus_auth['gas_client_secret']
  GLOBUS_AUTH_LOGOUT_URI = "https://auth.globus.org/v2/web/logout"

  # Set validity of pre-signed POST requests (in seconds)
  AWS_SIGNED_REQUEST_EXPIRATION = 60

  AWS_S3_INPUTS_BUCKET = "mpcs-cc-gas-inputs"
  AWS_S3_RESULTS_BUCKET = "mpcs-cc-gas-results"
  # Set the S3 key (object name) prefix to your CNetID
  # Keep the trailing '/' if using my upload code in views.py
  AWS_S3_KEY_PREFIX = "<CNetID>/"
  AWS_S3_ACL = "private"
  AWS_S3_ENCRYPTION = "AES256"

  AWS_GLACIER_VAULT = "mpcs-cc"

  # Change the ARNs below to reflect your SNS topics
  AWS_SNS_JOB_REQUEST_TOPIC = \
    "some-arn-job-requests:<CNetID>_job_requests"
  AWS_SNS_JOB_COMPLETE_TOPIC = \
    "some-arn-job-results:<CNetID>_job_results"

  # Change the table name to your own
  AWS_DYNAMODB_ANNOTATIONS_TABLE = "<CNetID>_annotations"

  # Change the email address to your username
  MAIL_DEFAULT_SENDER = "<CNetID>@mpcs-cc.com"

  # Time before free user results are archived (in seconds)
  FREE_USER_DATA_RETENTION = 300

class DevelopmentConfig(Config):
  DEBUG = True
  GAS_LOG_LEVEL = 'DEBUG'

class ProductionConfig(Config):
  DEBUG = False
  GAS_LOG_LEVEL = 'INFO'
  WSGI_SERVER = 'gunicorn.error'

class StagingConfig(Config):
  STAGING = True

class TestingConfig(Config):
  TESTING = True

### EOF
