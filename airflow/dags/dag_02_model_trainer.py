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

# O Scheduler varre o bucket ativamente para compilar o desenho visual da DAG
try:
    s3_endpoint = os.environ.get('AWS_S3_ENDPOINT', 'http://minio:9000')
    s3_client = boto3.client('s3', endpoint_url=s3_endpoint, region_name='us-east-1')
    contracts_response = s3_client.list_objects_v2(Bucket='model-contracts').get('Contents', [])
    contract_keys = [c['Key'] for c in contracts_response]
except Exception as e:
    print(f"Erro ao buscar contratos (MinIO fora do ar na avaliacao do Scheduler): {e}")
    contract_keys = []

with DAG(
    'DAG_02_Model_Trainer',
    default_args=default_args,
    description='Pipeline MLOps Corporativo terceirizando treino para Imagens Isoladas (DinD)',
    schedule_interval=timedelta(days=1),
    start_date=datetime(2025, 1, 1),
    catchup=False,
    tags=['dind', 'mlops', 'contract-driven'],
) as dag:

    for contract in contract_keys:
        task_id_name = contract.replace(".yaml", "").replace("-", "_")
        
        DockerOperator(
            task_id=f'train_isolated_worker_{task_id_name}',
            image='worker-mlops:latest',
            api_version='auto',
            auto_remove=True,
            network_mode='mlops-net',
            docker_url='unix://var/run/docker.sock',
            environment={
                'AWS_ACCESS_KEY_ID': os.environ.get('AWS_ACCESS_KEY_ID', 'minioadmin'),
                'AWS_SECRET_ACCESS_KEY': os.environ.get('AWS_SECRET_ACCESS_KEY', 'minioadmin'),
                'MLFLOW_S3_ENDPOINT_URL': os.environ.get('MLFLOW_S3_ENDPOINT_URL', 'http://minio:9000'),
                'MLFLOW_TRACKING_URI': os.environ.get('MLFLOW_TRACKING_URI', 'http://mlflow-server:5000')
            },
            command=f"python train.py --contract {contract}",
            mount_tmp_dir=False,
        )
