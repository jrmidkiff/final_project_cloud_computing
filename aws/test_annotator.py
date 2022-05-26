import boto3

s3 = boto3.client('s3')
response = s3.upload_file(
    Filename='/home/ec2-user/mpcs-cc/gas_annotator.zip', 
    Bucket='mpcs-cc-students', 
    Key='jmidkiff/gas_annotator.zip')
print(response)