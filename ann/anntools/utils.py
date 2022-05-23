# utils.py
#
# Original code by: Vlad Makarov, Chris Yoon
# Original copyright (c) 2011, The Mount Sinai School of Medicine
# Available under BSD licence
#
# Modified code copyright (C) 2011-2019 Vas Vasiliadis
# University of Chicago
#
##
__author__ = 'Vas Vasiliadis <vas@uchicago.edu>'


import os
import json
import pymysql
import boto3
from botocore.exceptions import ClientError

"""Get connection to reference database
"""
def db_connect():
    AWS_REGION_NAME = os.environ['AWS_REGION_NAME'] if \
        ('AWS_REGION_NAME' in  os.environ) else "us-east-1"

    # Get RDS secret from AWS Secrets Manager
    asm = boto3.client('secretsmanager', region_name=AWS_REGION_NAME)
    try:
        asm_response = asm.get_secret_value(SecretId='rds/anntools_database')
        rds_secret = json.loads(asm_response['SecretString'])
    except ClientError as e:
        print(f"Unable to retrieve RDS credentials from AWS Secrets Manager: {e}")
        raise e

    # Extract database connection parameters
    rds_host = rds_secret['host']
    mysql_port = rds_secret['port']
    username = rds_secret['username']
    password = rds_secret['password']
    database_name = 'annotator'

    # Return a connection to the database
    return pymysql.connect(
        host=rds_host,
        port=mysql_port,
        user=username,
        passwd=password,
        db=database_name)


"""Column inices for pileup and VCF
"""
def getFormatSpecificIndices(format='vcf'):
    chr_ind = 0
    pos_ind = 1
    ref_ind = 3
    alt_ind = 4

    if (format !='vcf'):
        ref_ind = 2
        alt_ind = 3

    return [chr_ind, pos_ind, ref_ind, alt_ind]


"""Helper method to determine if two regions overlap
"""
def isOverlap(testStart, testEnd, refStart, refEnd):
    if (((testStart <= refStart) and (testEnd >= refStart)) or \
        ((testStart >= refStart) and (testStart <= refEnd))):
        return True
    else:
        return False


"""Overlap between segments
"""
def getOverlap(testStart, testEnd, refStart, refEnd):
    return max(0, (min(testEnd, refEnd) - max(testStart, refStart) + 1))


"""Helper method to calculate proportion of a CNV is in the segdup or other region
Accepts numeric data, such as integer or float type
"""
def proportionOverlap(testStart, testEnd, refStart, refEnd):
    cnvlength = (testEnd - testStart) + 1
    overlaplength = getOverlap(testStart, testEnd, refStart, refEnd)
    pctover = (float(overlaplength)/cnvlength) * 100
    return round(pctover, 2)


"""Helper method to determine if the location is within the region
"""
def isBetween(testStart, refStart, refEnd):
    if ((refStart<=testStart) and (testStart <= refEnd)):
        return True
    else:
        return False


"""Helper method to deduplicate the list
"""
def dedup(mylist):
    outlist = []
    for element in mylist:
        if element not in outlist:
            outlist.append(element)
    return outlist


"""Helper method to parse fields
"""
def parse_field(text, key, sep1, sep2):
    fields = text.strip().split(sep1)
    for f in fields:
        pairs = f.split(sep2)
        if (str(pairs[0]).find(str(key)) > -1):
            return str(pairs[1])
    return '.'

### EOF