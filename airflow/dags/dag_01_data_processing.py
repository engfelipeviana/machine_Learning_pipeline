import os
import boto3
from airflow import DAG
from airflow.providers.docker.operators.docker import DockerOperator
from datetime import datetime, timedelta

default_args = {
    'owner': 'squad-data',
    'depends_on_past': False,
    'retries': 0,
}

try:
    s3_endpoint = os.environ.get('AWS_S3_ENDPOINT', 'http://minio:9000')
    s3_client = boto3.client('s3', endpoint_url=s3_endpoint, region_name='us-east-1')
    manifests = s3_client.list_objects_v2(Bucket='model-contracts').get('Contents', [])
    contract_keys = [c['Key'] for c in manifests]
except Exception as e:
    contract_keys = []

with DAG(
    'DAG_01_Data_Processing',
    default_args=default_args,
    description='Medallion Pipeline ELT: Landing Zone -> Raw -> Trusted (Iceberg)',
    schedule_interval=timedelta(days=1),
    start_date=datetime(2025, 1, 1),
    catchup=False,
    tags=['data-engineering', 'elt', 'medallion', 'iceberg'],
) as dag:

    for contract in contract_keys:
        task_id_name = contract.replace(".yaml", "").replace("-", "_")
        
        env_vars = {
            'AWS_ACCESS_KEY_ID': os.environ.get('AWS_ACCESS_KEY_ID', 'minioadmin'),
            'AWS_SECRET_ACCESS_KEY': os.environ.get('AWS_SECRET_ACCESS_KEY', 'minioadmin'),
            'AWS_S3_ENDPOINT': os.environ.get('AWS_S3_ENDPOINT', 'http://minio:9000'),
        }

        task_raw = DockerOperator(
            task_id=f'landing_to_raw_{task_id_name}',
            image='worker-data:latest',
            api_version='auto',
            auto_remove=True,
            network_mode='mlops-net',
            docker_url='unix://var/run/docker.sock',
            environment=env_vars,
            command=f"--layer raw --contract {contract}",
            mount_tmp_dir=False,
        )

        task_trusted = DockerOperator(
            task_id=f'raw_to_trusted_{task_id_name}',
            image='worker-data:latest',
            api_version='auto',
            auto_remove=True,
            network_mode='mlops-net',
            docker_url='unix://var/run/docker.sock',
            environment=env_vars,
            command=f"--layer trusted --contract {contract}",
            mount_tmp_dir=False,
        )

        task_raw >> task_trusted
