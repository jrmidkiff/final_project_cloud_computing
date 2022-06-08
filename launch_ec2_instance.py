import boto3
import sys

def main(word=''): 
    ec2 = boto3.resource('ec2')
    cnet_id = 'jmidkiff'
    if word == '': 
        key_value = cnet_id
    else: 
        key_value = cnet_id + '-' + word
    ami = 'ami-0627971cd8c777781'
    instances = ec2.create_instances(
        MinCount=1,
        MaxCount=1,
        ImageId=ami,
        InstanceType='t2.nano',
        IamInstanceProfile={'Name': 'instance_profile_' + cnet_id},
        TagSpecifications=[{
            'ResourceType': 'instance',
            'Tags': [{'Key': 'Name', 'Value': key_value}]
            }],
        KeyName=cnet_id,
        SecurityGroups=['mpcs-cc']
    )
    instance = instances[0]
    print(instance.id)
    instance.wait_until_running()
    ec2_client = boto3.client('ec2')
    info = ec2_client.describe_instances(
        InstanceIds=[instance.id]
        )['Reservations'][0]['Instances'][0]
    print(info["PublicDnsName"])
    print(f'ssh -i "C:\\Users\\jrmid\\.ssh\\jmidkiff.pem" ec2-user@{info["PublicDnsName"]}')

if __name__ == '__main__': 
    if len(sys.argv) > 1: 
        main(sys.argv[1])
    else: 
        main()