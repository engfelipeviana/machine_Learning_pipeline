import pandas as pd
import boto3
from botocore.client import Config
import os

# MinIO Connection Configuration
MINIO_ENDPOINT = os.getenv('AWS_S3_ENDPOINT', 'http://minio:9000')
MINIO_ACCESS_KEY = os.getenv('AWS_ACCESS_KEY_ID', 'minioadmin')
MINIO_SECRET_KEY = os.getenv('AWS_SECRET_ACCESS_KEY', 'minioadmin')
BUCKET_NAME = 'landing_zone'
FILE_NAME = 'powerbi_refresh_audit.csv'
FILE_PATH = f'./{FILE_NAME}'

print(f"Connecting to MinIO at {MINIO_ENDPOINT}...")

# Initialize S3 Client (boto3) compatible with MinIO
s3_client = boto3.client(
    's3',
    endpoint_url=MINIO_ENDPOINT,
    aws_access_key_id=MINIO_ACCESS_KEY,
    aws_secret_access_key=MINIO_SECRET_KEY,
    config=Config(signature_version='s3v4'),
    region_name='us-east-1'
)

# Create bucket if it doesn't exist (failsafe in case minio-init didn't run)
try:
    s3_client.head_bucket(Bucket=BUCKET_NAME)
    print(f"Bucket '{BUCKET_NAME}' already exists.")
except Exception as e:
    print(f"Bucket '{BUCKET_NAME}' not found. Creating it...")
    s3_client.create_bucket(Bucket=BUCKET_NAME)

# Upload the file
print(f"Uploading {FILE_NAME} to bucket {BUCKET_NAME}...")
try:
    s3_client.upload_file(FILE_PATH, BUCKET_NAME, FILE_NAME)
    print("Upload completed successfully! 🚀")
except Exception as e:
    print(f"Error uploading file: {e}")

# Verify upload
print("\nFiles in landing_zone:")
response = s3_client.list_objects_v2(Bucket=BUCKET_NAME)
if 'Contents' in response:
    for obj in response['Contents']:
        print(f" - {obj['Key']} ({obj['Size']} bytes)")
