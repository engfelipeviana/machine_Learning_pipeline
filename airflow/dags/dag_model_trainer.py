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
    s3_client = boto3.client('s3', endpoint_url='http://minio:9000', aws_access_key_id='minioadmin', aws_secret_access_key='minioadmin', region_name='us-east-1')
    contracts_response = s3_client.list_objects_v2(Bucket='model-contracts').get('Contents', [])
    contract_keys = [c['Key'] for c in contracts_response]
except Exception as e:
    print(f"Erro ao buscar contratos (MinIO fora do ar na avaliacao do Scheduler): {e}")
    contract_keys = []

with DAG(
    'MLOps_DinD_Contract_Pipeline',
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
            command=f"python train.py --contract {contract}",
            mount_tmp_dir=False,
        )
