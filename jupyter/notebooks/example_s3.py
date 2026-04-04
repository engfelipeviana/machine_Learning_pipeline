import boto3
import pandas as pd
import os

# AWS configs based on docker-compose and environment variables
s3_client = boto3.client(
    's3',
    endpoint_url=os.getenv('AWS_S3_ENDPOINT', 'http://minio:9000'),
    aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID', 'minioadmin'),
    aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY', 'minioadmin')
)

# List buckets
print("Buckets:")
response = s3_client.list_buckets()
for bucket in response['Buckets']:
    print(f"  {bucket['Name']}")

# Create some sample data
df = pd.DataFrame({
    'id': [1, 2, 3],
    'name': ['Alice', 'Bob', 'Charlie']
})

# Needs s3fs to write to s3 endpoint. 
# Alternatively, write to local and upload:
df.to_parquet('sample.parquet')
s3_client.upload_file('sample.parquet', 'mlops-data', 'sample.parquet')
print("Uploaded sample.parquet to s3://mlops-data/sample.parquet")
