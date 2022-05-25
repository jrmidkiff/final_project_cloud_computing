# views.py
#
# Copyright (C) 2011-2020 Vas Vasiliadis
# University of Chicago
#
# Application logic for the GAS
#
##
__author__ = 'Vas Vasiliadis <vas@uchicago.edu>'

import uuid
import time
import json
from datetime import datetime

import boto3
from boto3.dynamodb.conditions import Key
from botocore.client import Config
from botocore.exceptions import ClientError, ParamValidationError

from flask import (abort, flash, redirect, render_template,
  request, session, url_for)

from gas import app, db
from decorators import authenticated, is_premium
from auth import get_profile, update_profile

import re
UUID_REGEX = '[0-9A-Fa-f]{8}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{12}'
dynamodb = boto3.client('dynamodb')
sqs = boto3.client('sqs')
s3 = boto3.client('s3')

"""Start annotation request
Create the required AWS S3 policy document and render a form for
uploading an annotation input file using the policy document.

Note: You are welcome to use this code instead of your own
but you can replace the code below with your own if you prefer.
"""
@app.route('/annotate', methods=['GET'])
@authenticated
def annotate():
  # Create a session client to the S3 service
  
  s3 = boto3.client('s3',
    region_name=app.config['AWS_REGION_NAME'],
    config=Config(signature_version='s3v4'))

  bucket_name = app.config['AWS_S3_INPUTS_BUCKET']
  user_id = session['primary_identity'] # Globus Identity ID is a UUID
  
  # Generate unique ID to be used as S3 key (name)
  key_name = app.config['AWS_S3_KEY_PREFIX'] + user_id + '/' + \
    str(uuid.uuid4()) + '~${filename}'

  # Create the redirect URL
  redirect_url = str(request.url) + '/job'

  # Define policy fields/conditions
  encryption = app.config['AWS_S3_ENCRYPTION']
  acl = app.config['AWS_S3_ACL']
  fields = {
    "success_action_redirect": redirect_url,
    "x-amz-server-side-encryption": encryption,
    "acl": acl
  }
  conditions = [
    ["starts-with", "$success_action_redirect", redirect_url],
    {"x-amz-server-side-encryption": encryption},
    {"acl": acl}
  ]

  # Generate the presigned POST call
  try:
    presigned_post = s3.generate_presigned_post(
      Bucket=bucket_name, 
      Key=key_name,
      Fields=fields,
      Conditions=conditions,
      ExpiresIn=app.config['AWS_SIGNED_REQUEST_EXPIRATION'])
  except ClientError as e:
    app.logger.error(f"Unable to generate presigned URL for upload: {e}")
    return abort(500)
    
  # Render the upload form which will parse/submit the presigned POST
  return render_template('annotate.html', s3_post=presigned_post)


"""Fires off an annotation job
Accepts the S3 redirect GET request, parses it to extract 
required info, saves a job item to the database, and then
publishes a notification for the annotator service.

Note: Update/replace the code below with your own from previous
homework assignments
"""
@app.route('/annotate/job', methods=['GET'])
@authenticated
def create_annotation_job_request():

    # Get bucket name, key, and job ID from the S3 redirect URL
    bucket_name = str(request.args.get('bucket'))
    s3_key = str(request.args.get('key'))
    
    # Extract the job ID from the S3 key
    owner, _, uu_id_file_name = s3_key.split('/')
    uu_id, file_name = uu_id_file_name.split('~')
    user_id = session['primary_identity'] # Globus Identity ID is a UUID
    
    if not file_name.endswith('.vcf'): # File still gets uploaded though
        abort(405)

    # Persist job to database
    dynamodb = boto3.client('dynamodb')
    data = {
        "job_id": uu_id,
        "user_id": user_id, 
        'input_file_name': file_name, 
        's3_inputs_bucket': bucket_name, 
        's3_key_input_file': s3_key, 
        'submit_time': time.time(), 
        'job_status': 'PENDING'
    }
    dynamo_data = {}
    for key, value in data.items(): 
        if type(value) == str: 
            dynamo_data[key] = {'S': value}
        elif type(value) == float: 
            dynamo_data[key] = {'N': str(value)}
    
    try: 
        dynamodb.put_item(
            TableName=app.config['AWS_DYNAMODB_ANNOTATIONS_TABLE'], 
            Item=dynamo_data, 
            ConditionExpression='attribute_not_exists(job_id)'
        )
    except ClientError as e: # Job was already uploaded to cloud
        code = e.response['Error']['Code']
        if code == 'ConditionalCheckFailedException': 
            abort(405)    
        else: 
            abort(500)

    # Send message to request queue
    sns = boto3.client('sns')
    try: 
        user_email = session['email']
        dynamo_data['user_email'] = {'S': user_email}
        response = sns.publish(
            TopicArn= app.config['AWS_SNS_JOB_REQUEST_TOPIC'],
            Message=str(dynamo_data)
        )
    except exceptions.ClientError as e: # Topic not found
        code = e.response['Error']['Code']
        if code == 'NotFound': 
            abort(404) 
        else: 
            abort(500)  

    return render_template('annotate_confirm.html', job_id=uu_id)


"""List all annotations for the user
"""
@app.route('/annotations', methods=['GET'])
@authenticated
def annotations_list():

  # Get list of annotations to display
    try: 
        response = dynamodb.query(
            TableName=app.config['AWS_DYNAMODB_ANNOTATIONS_TABLE'], 
            IndexName="user_id_index",
            Select='SPECIFIC_ATTRIBUTES', 
            ProjectionExpression="job_id, submit_time, input_file_name, job_status", 
            KeyConditionExpression="user_id = :u", 
            ExpressionAttributeValues={":u": {
                "S": session['primary_identity']}}
        )
    except ClientError as e: 
        abort(500)
    
    l = []
    for item in response['Items']:
        d = {}
        d['job_id'] = item['job_id']['S']
        # https://docs.python.org/3/library/time.html#time.localtime
        d['submit_time'] = time.asctime(time.localtime(float(item['submit_time']['N'])))
        d['input_file_name'] = item['input_file_name']['S']
        d['job_status'] = item['job_status']['S']
        l.append(d)
    l.reverse() # Faster to append then reverse rather than to insert(0)
    
    return render_template('annotations.html', annotations=l)


"""Display details of a specific annotation job
"""
@app.route('/annotations/<id>', methods=['GET'])
@authenticated
def annotation_details(id):
    try: # Get DynamoDB Record
        response = dynamodb.get_item(
            TableName=app.config['AWS_DYNAMODB_ANNOTATIONS_TABLE'], 
            Key={'job_id': {'S': id}})
    # https://stackoverflow.com/a/68521788/8527838
    except dynamodb.exceptions.ResourceNotFoundException: # Error - Table missing
        abort(500)   
    try: # Get DynamoDB Record
        rv = response['Item']
    except KeyError: # No result
        abort(404)
    if rv['user_id']['S'] != session['primary_identity']: 
        abort(403)
    annotation = {}
    annotation['job_id'] = rv['job_id']['S']
    annotation['submit_time'] = time.asctime(time.localtime(float(rv['submit_time']['N'])))
    annotation['input_file_name'] = rv['input_file_name']['S']
    annotation['job_status'] = rv['job_status']['S']
    free_access_expired = False
    restore_message = False
    if annotation['job_status'] == 'COMPLETED': 
        complete_time = float(rv['complete_time']['N'])
        annotation['complete_time'] = time.asctime(time.gmtime(complete_time))
        # https://boto3.amazonaws.com/v1/documentation/api/latest/guide/s3-presigned-urls.html
        if (time.time() - complete_time >= app.config['FREE_USER_DATA_RETENTION']) and session['role'] == 'free_user':             
            free_access_expired = True
        elif 's3_key_result_file' not in rv.keys(): # Files are being unarchived
            restore_message = True
            annotation['restore_message'] = "This file is currently being unarchived from deep storage and should be available within several hours after conversion to premium plan. Please check back later."
        else:  
            try: # Download results file to user
                response = s3.generate_presigned_url(
                    ClientMethod='get_object', 
                    Params={
                        'Bucket': app.config["AWS_S3_RESULTS_BUCKET"], 
                        'Key': rv['s3_key_result_file']['S']}, 
                    ExpiresIn=120)
            except ClientError as e: 
                abort(500)
            annotation['result_file_url'] = response
        annotation['s3_key_log_file'] = rv['s3_key_log_file']['S']
    
    return render_template('annotation_details.html', 
        annotation=annotation, free_access_expired=free_access_expired)

"""Display the log file contents for an annotation job
"""
# https://flask.palletsprojects.com/en/2.1.x/quickstart/
@app.route('/annotations/<id>/log', methods=['GET'])
@authenticated
def annotation_log(id):
    s3_key_log_file = request.args.get('s3_key_log_file')
    try: 
        response = s3.get_object(
            Bucket=app.config['AWS_S3_RESULTS_BUCKET'],
            Key=s3_key_log_file)
    except ClientError as e: 
        code = e.response['Error']['Code']
        if code == 'NoSuchKey' or code == 'NoSuchBucket': 
            abort(404)
        else: 
            abort(500)
    except ParamValidationError as e: 
        abort(404)

    log_file_contents = response['Body'].read().decode()

    return render_template('view_log.html', job_id=id, log_file_contents=log_file_contents) # log_file_contents)


"""Subscription management handler
"""
@app.route('/subscribe', methods=['GET', 'POST'])
@authenticated
def subscribe():
    if (request.method == 'GET'):
        # Display form to get subscriber credit card info
        if (session.get('role') == "free_user"):
            return render_template('subscribe.html')
        else:
            return redirect(url_for('profile'))

    elif (request.method == 'POST'):
        # Update user role to allow access to paid features
        update_profile(
            identity_id=session['primary_identity'],
            role="premium_user")

        # Update role in the session
        session['role'] = "premium_user"

        # Request restoration of the user's data from Glacier
        # Add code here to initiate restoration of archived user data
        # Make sure you handle files not yet archived!
        sqs.send_message( 
            QueueUrl=app.config['AWS_SQS_RESTORE_QUEUE_URL'], 
            MessageBody=str({
                'user_id': session['primary_identity']})
        )

    # Display confirmation page
    return render_template('subscribe_confirm.html') 

"""Reset subscription
"""
# MUST MAKE CHANGES THAT RE-ARCHIVE ALL OF A USER'S NON-ARCHIVED FILES IF THEY REVERT TO FREE
@app.route('/unsubscribe', methods=['GET'])
@authenticated
def unsubscribe():
  # Hacky way to reset the user's role to a free user; simplifies testing
  update_profile(
    identity_id=session['primary_identity'],
    role="free_user"
  )
  return redirect(url_for('profile'))


"""DO NOT CHANGE CODE BELOW THIS LINE
*******************************************************************************
"""

"""Home page
"""
@app.route('/', methods=['GET'])
def home():
  return render_template('home.html')

"""Login page; send user to Globus Auth
"""
@app.route('/login', methods=['GET'])
def login():
  app.logger.info(f"Login attempted from IP {request.remote_addr}")
  # If user requested a specific page, save it session for redirect after auth
  if (request.args.get('next')):
    session['next'] = request.args.get('next')
  return redirect(url_for('authcallback'))

"""404 error handler
"""
@app.errorhandler(404)
def page_not_found(e):
  return render_template('error.html', 
    title='Page not found', alert_level='warning',
    message="The page you tried to reach does not exist. \
      Please check the URL and try again."
    ), 404

"""403 error handler
"""
@app.errorhandler(403)
def forbidden(e):
  return render_template('error.html',
    title='Not authorized', alert_level='danger',
    message="You are not authorized to access this page. \
      If you think you deserve to be granted access, please contact the \
      supreme leader of the mutating genome revolutionary party."
    ), 403

"""405 error handler
"""
@app.errorhandler(405)
def not_allowed(e):
  return render_template('error.html',
    title='Not allowed', alert_level='warning',
    message="You attempted an operation that's not allowed; \
      get your act together, hacker!"
    ), 405

"""500 error handler
"""
@app.errorhandler(500)
def internal_error(error):
  return render_template('error.html',
    title='Server error', alert_level='danger',
    message="The server encountered an error and could \
      not process your request."
    ), 500

### EOF
