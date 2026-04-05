import argparse
import boto3
import pandas as pd
import io
import os
import s3fs
import yaml
from sqlalchemy import create_engine, text
import warnings

warnings.filterwarnings('ignore')

def process_contract(contract_key):
    MINIO_ENDPOINT = os.getenv('AWS_S3_ENDPOINT', 'http://minio:9000')
    MINIO_ACCESS_KEY = os.getenv('AWS_ACCESS_KEY_ID', 'minioadmin')
    MINIO_SECRET_KEY = os.getenv('AWS_SECRET_ACCESS_KEY', 'minioadmin')
    
    print(f"=== Data Worker Iniciado: {contract_key} ===")
    s3_client = boto3.client(
        's3', endpoint_url=MINIO_ENDPOINT,
        aws_access_key_id=MINIO_ACCESS_KEY,
        aws_secret_access_key=MINIO_SECRET_KEY,
        region_name='us-east-1'
    )
    
    response_yaml = s3_client.get_object(Bucket='model-contracts', Key=contract_key)
    contract = yaml.safe_load(response_yaml['Body'].read())
    
    landing_bucket = contract['data']['bucket']
    file_name = contract['data']['file_name']
    
    print(f"\n[1] Lendo Data Bruta: {landing_bucket}/{file_name} ...")
    response = s3_client.get_object(Bucket=landing_bucket, Key=file_name)
    df = pd.read_csv(io.BytesIO(response['Body'].read()))
    print(f"Tamanho extraído: {df.shape} linhas x colunas")
    
    raw_bucket = 'raw'
    # Utilizar o nome do modelo limpo para nomear a tabela Parquet no Lakehouse
    table_name = contract['metadata']['name'].replace('_model', '')
    s3_path = f"s3://{raw_bucket}/{table_name}/{table_name}_data.parquet"
    
    print(f"\n[2] Convertendo arquivo para Parquet Nativo ({s3_path})...")
    s3_fs = s3fs.S3FileSystem(
        key=MINIO_ACCESS_KEY,
        secret=MINIO_SECRET_KEY,
        client_kwargs={'endpoint_url': MINIO_ENDPOINT}
    )
    df.to_parquet(s3_path, filesystem=s3_fs, index=False)
    print("Salvo no MinIO Bucket 'raw' com sucesso.")
    
    print(f"\n[3] Catalogando Dataset Iceberg no Trino (Tabela: minio.raw.{table_name})...")
    # Conectando usando SQLAlchemy wrapper do Trino
    trino_engine = create_engine('trino://jovyan@trino:8080/minio')
    
    with trino_engine.connect() as con:
        # Schema definition matching Iceberg
        con.execute(text("CREATE SCHEMA IF NOT EXISTS minio.raw WITH (location = 's3://raw/')"))
        # Using built-in append mode which creates ICEBERG native parquet layout in Trino metadata
        df.to_sql(table_name, con=trino_engine, schema='raw', if_exists='replace', index=False, method='multi', chunksize=1000)
        
        print("Catalogo atualizado. Data validada e pronta no Data Warehouse para Modelagem!")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='MLOps Data Process Worker')
    parser.add_argument('--contract', type=str, required=True, help='Nome do contrato YAML no Bucket S3')
    args = parser.parse_args()
    process_contract(args.contract)
