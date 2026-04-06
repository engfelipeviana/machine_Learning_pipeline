import argparse
import boto3
import pandas as pd
import io
import os
from datetime import datetime
import s3fs
import yaml
from sqlalchemy import create_engine, text
import warnings

warnings.filterwarnings('ignore')

def get_boto_client():
    MINIO_ENDPOINT = os.getenv('AWS_S3_ENDPOINT', 'http://minio:9000')
    MINIO_ACCESS_KEY = os.getenv('AWS_ACCESS_KEY_ID', 'minioadmin')
    MINIO_SECRET_KEY = os.getenv('AWS_SECRET_ACCESS_KEY', 'minioadmin')
    return boto3.client(
        's3', endpoint_url=MINIO_ENDPOINT,
        aws_access_key_id=MINIO_ACCESS_KEY,
        aws_secret_access_key=MINIO_SECRET_KEY,
        region_name='us-east-1'
    )

def get_s3fs():
    return s3fs.S3FileSystem(
        key=os.getenv('AWS_ACCESS_KEY_ID', 'minioadmin'),
        secret=os.getenv('AWS_SECRET_ACCESS_KEY', 'minioadmin'),
        client_kwargs={'endpoint_url': os.getenv('AWS_S3_ENDPOINT', 'http://minio:9000')}
    )

def process_raw(contract_key):
    print(f"=== [LAYER RAW] Iniciado: {contract_key} ===")
    s3_client = get_boto_client()
    contract = yaml.safe_load(s3_client.get_object(Bucket='model-contracts', Key=contract_key)['Body'].read())
    
    landing_bucket = contract['data']['bucket']
    file_name = contract['data']['file_name']
    
    print(f"[1] Extraindo {file_name} da {landing_bucket}...")
    df = pd.read_csv(io.BytesIO(s3_client.get_object(Bucket=landing_bucket, Key=file_name)['Body'].read()))
    
    table_name = contract['data']['file_name'].replace('.csv', '')
    s3_path = f"s3://raw/{table_name}/{table_name}_data.parquet"
    
    print(f"[2] Convertendo brutos para Parquet ({s3_path})...")
    df.to_parquet(s3_path, filesystem=get_s3fs(), index=False)
    
    print(f"[3] Catalogando minio.raw.{table_name} no Trino...")
    trino_engine = create_engine('trino://jovyan@trino:8080/minio')
    with trino_engine.connect() as con:
        con.execute(text("CREATE SCHEMA IF NOT EXISTS minio.raw WITH (location = 's3://raw/')"))
        df.to_sql(table_name, con=trino_engine, schema='raw', if_exists='replace', index=False, method='multi', chunksize=1000)

def process_trusted(contract_key):
    print(f"=== [LAYER TRUSTED] Iniciado: {contract_key} ===")
    s3_client = get_boto_client()
    contract = yaml.safe_load(s3_client.get_object(Bucket='model-contracts', Key=contract_key)['Body'].read())
    table_name = contract['data']['file_name'].replace('.csv', '')
    
    print(f"[1] Carregando parquet da Camada RAW via Trino...")
    trino_engine = create_engine('trino://jovyan@trino:8080/minio')
    query = f"SELECT * FROM minio.raw.{table_name}"
    df = pd.read_sql(query, con=trino_engine)
    
    print(f"[2] Aplicando Curadoria (Drop NA Data Quality Rule)...")
    tamanho_original = df.shape[0]
    df = df.dropna()
    tamanho_curado = df.shape[0]
    print(f"Qualidade: {tamanho_original - tamanho_curado} registros inválidos removidos.")
    
    s3_path = f"s3://trusted/{table_name}/{table_name}_trusted.parquet"
    
    df['ingestion_date'] = datetime.now()
    try:
        df_old = pd.read_parquet(s3_path, filesystem=get_s3fs())
        df = pd.concat([df_old, df], ignore_index=True)
        print(f"Append Realizado. O Iceberg agora possui {len(df)} registros acumulados no tempo.")
    except Exception:
        print("Criando primeiro snapshot da tabela Trusted.")

    print(f"[3] Salvando parquets acumulados na camada TRUSTED ({s3_path})...")
    df.to_parquet(s3_path, filesystem=get_s3fs(), index=False)
    
    print(f"[4] Catalogando minio.trusted.{table_name} no Trino...")
    with trino_engine.connect() as con:
        con.execute(text("CREATE SCHEMA IF NOT EXISTS minio.trusted WITH (location = 's3://trusted/')"))
        df.to_sql(table_name, con=trino_engine, schema='trusted', if_exists='replace', index=False, method='multi', chunksize=1000)
    print("Processamento Ouro (Trusted) Concluído com Sucesso!")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='MLOps Data Curador')
    parser.add_argument('--contract', type=str, required=True, help='Yaml do modelo')
    parser.add_argument('--layer', type=str, choices=['raw', 'trusted'], required=True, help='Camada medallion alvo do job')
    args = parser.parse_args()
    
    if args.layer == 'raw':
        process_raw(args.contract)
    elif args.layer == 'trusted':
        process_trusted(args.contract)
