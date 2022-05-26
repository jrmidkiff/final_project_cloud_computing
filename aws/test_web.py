import boto3

s3 = boto3.client('s3')
response = s3.upload_file(
    Filename='/home/ec2-user/mpcs-cc/gas_web_server.zip', 
    Bucket='mpcs-cc-students', 
    Key='jmidkiff/gas_web_server.zip')
print(response)