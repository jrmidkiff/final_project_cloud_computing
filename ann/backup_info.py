session: <SecureCookieSession {
    'email': 'jmidkiff@uchicago.edu', 
    'institution': 'None', 
    'is_authenticated': True, 
    'name': 'James Midkiff', 
    'primary_identity': 'f5b42957-b7ac-4ecb-af5c-a5d61c72bea2', 
    'primary_username': 'jmidkiff@uchicago.edu', 
    'role': 'free_user', 
    'tokens': {
        'auth.globus.org': {
            'access_token': 'AgwlE6vQ5m77vplnPKjbE5K2ObvMD9zmeNerv5prkjzb8XbnVbulCE6z8OD5DKpm4Ov4XKY4jlP6VjF8Gwl4vi2D4GPiwn523FWJ7wX', 
            'expires_at_seconds': 1653343973, 
            'refresh_token': 'AgKgbYDo1rbx0v8VaEJ2Ww2D05oxgnKdl8E6b0gBlpDyneadvqugU1G1paPrkOBd9oKvlpbx4e6BjvK93jOPjYNe5MYgx', 
            'resource_server': 'auth.globus.org', 
            'scope': 'openid profile email', 
            'token_type': 'Bearer'
        }, 
        'transfer.api.globus.org': {
            'access_token': 'Ag9rNkGq8Dk2B17ykVbzpjerjYmK1kBYMgqPOnmdx55rON3NOqFpC4YBnyo4YrjxyrXpvJW4lpo74JHBYPw60IqX0Pa', 
            'expires_at_seconds': 1653343973, 
            'refresh_token': 'AgwekaBEle0Gdv6p8bm4PyqlOmeOB7r8pYMvbW6dPdm1QGwgykUJUx7avNjOd1dao7J3jM24K9eqbxlOkg7dvlmr9dJWe', 
            'resource_server': 'transfer.api.globus.org', 
            'scope': 'urn:globus:auth:scope:transfer.api.globus.org:all', 
            'token_type': 'Bearer'
        }
    }
}>
event = {
    'Records': [{
        'messageId': 'af9672f8-7258-4d46-a635-83d0e116cad1', 
        'receiptHandle': 'AQEBYJTzBmKTo4Ruvlk+vAqRqwRdfts1WMzqDCWCV3qi+JLpMYbzWB04IAQoHx5WlgmWjc/c4/C++nPUDSt+jzkAxtbvq+MCMhAjKWqdVepkPfbxqSB+O9mZmQEgeP731LXe7wdiz+6df2wij3iJCp1ktu0Hv/AtNRmwppsgKeN3oKNXm4s9vQ+AEtOJ4Kddmrbjyd/O4zxulBe+9SDbqe2l2r+susn3kCzJCL0pTcrOUXYgrphLlpBaQ1gSIJqfcjSXgUCdIweEk0+6ZJCwhK0BkzCDueRX6eiC67tbEHyjrylQ6yCyGG9xg8QW/zWtouD2MlXgHlwJz/s5uU2E2naOhaN8TK8vMpTCekF5T50HaIUQ+yJHamUR19KW9NbAqU7dcSKWF0lnmVsJMLCDiowv6Q==', 
        'body': '{\n  "Type" : "Notification",\n  "MessageId" : "5bdb7c6a-af3c-58a6-9617-276f8f9ff043",\n  "TopicArn" : "arn:aws:sns:us-east-1:659248683008:jmidkiff_job_results",\n  "Message" : "{\'job_id\': \'2e4dc838-5b44-4051-9041-d72715369ad5\', \'user_email\': \'jmidkiff@uchicago.edu\', \'job_status\': \'COMPLETED\'}",\n  "Timestamp" : "2022-05-23T05:40:51.520Z",\n  "SignatureVersion" : "1",\n  "Signature" : "mClhDTNhjDLQ4Po8DJMjkM5krEXSYuxZHKcNCcwzGeETz0deQTOsXpfSO67Q7fiK0VcUrQg8L1vKfwTaYR0scx5cx6mQZDjWqqTob1ZSEt6+qt6mDTPM/2TqXwbrgYARc4HE8aEXVgGxtwaPQSkPtyco0xbpkuy35hhGe3V8aohnqlw5mHbCFtpkN3aesmC38sKJDoeBVglsrxVxrCKpTk1mgWlduI2G7SkinjWFHgPHcQAoHJRGYzI5MU86VS5ZGL8uYDtssz9RTl0JNF4JoaC9denionCNBtS97hB7hr1HAzXu+wBb0XBUufjKjvjF53TWdYOzlfY2+1mRUhX8rg==",\n  "SigningCertURL" : "https://sns.us-east-1.amazonaws.com/SimpleNotificationService-7ff5318490ec183fbaddaa2a969abfda.pem",\n  "UnsubscribeURL" : "https://sns.us-east-1.amazonaws.com/?Action=Unsubscribe&SubscriptionArn=arn:aws:sns:us-east-1:659248683008:jmidkiff_job_results:0d92e482-d5be-484c-bb19-910e970e521d"\n}', 
        'attributes': {
            'ApproximateReceiveCount': '1', 
            'SentTimestamp': '1653284451554', 
            'SenderId': 'AIDAIT2UOQQY3AUEKVGXU', 
            'ApproximateFirstReceiveTimestamp': '1653284451559'
        }, 
        'messageAttributes': {}, 
        'md5OfBody': '78692382f92ba090c2a207371d5e3a09', 
        'eventSource': 'aws:sqs', 
        'eventSourceARN': 'arn:aws:sqs:us-east-1:659248683008:jmidkiff_job_results', 
        'awsRegion': 'us-east-1'
    }]
}
