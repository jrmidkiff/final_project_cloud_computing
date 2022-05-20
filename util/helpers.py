# helpers.py
#
# Copyright (C) 2011-2019 Vas Vasiliadis
# University of Chicago
#
# Miscellaneous helper functions
#
##
__author__ = 'Vas Vasiliadis <vas@uchicago.edu>'

import os
import json
import boto3
from botocore.exceptions import ClientError

# Get util configuration
from configparser import SafeConfigParser
config = SafeConfigParser(os.environ)
config.read(os.path.join(os.path.abspath(os.path.dirname(__file__)), 'util_config.ini'))

"""Send email via Amazon SES
"""
def send_email_ses(recipients=None, 
  sender=None, subject=None, body=None):

  ses = boto3.client('ses', region_name=config['aws']['AwsRegionName'])

  try:
    response = ses.send_email(
      Destination = {
        'ToAddresses': (recipients if type(recipients) == "list" else [recipients])
      },
      Message={
        'Body': {'Text': {'Charset': "UTF-8", 'Data': body}},
        'Subject': {'Charset': "UTF-8", 'Data': subject},
      },
      Source=(sender or config['gas']['EmailDefaultSender']))
  except ClientError as e:
    raise ClientError

  return response


import psycopg2
import psycopg2.extras

"""Access user profile in accounts database
"""
def get_user_profile(id=None, db_name=None):
  # Get database connection details from AWS Secrets Manager
  asm = boto3.client('secretsmanager', region_name=config['aws']['AwsRegionName'])
  try:
    asm_response = asm.get_secret_value(SecretId='rds/accounts_database')
    rds_secret = json.loads(asm_response['SecretString'])
  except ClientError as e:
    raise ClientError

  db_uri = "postgresql://" + rds_secret['username'] + ':' + \
    rds_secret['password'] + '@' + rds_secret['host'] + ':' + \
    str(rds_secret['port']) + '/' + \
    (db_name or config['gas']['AccountsDatabase'])

  try:
    # Connect to accounts database and get a cursor
    connection = psycopg2.connect(db_uri)
    cursor = connection.cursor(cursor_factory = psycopg2.extras.DictCursor)
    
    # Query the database and get the user's profile record
    query_string = f"SELECT * FROM profiles WHERE identity_id = '{id}'"
    cursor.execute(query_string)
    profile = cursor.fetchall()[0]
  
  except psycopg2.Error as e:
    connection.rollback()
    raise psycopg2.Error

  # Return user profile record as a dict
  return profile

### EOF