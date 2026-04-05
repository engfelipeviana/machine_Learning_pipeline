import nbformat as nbf

nb = nbf.v4.new_notebook()

code_intro = """import pandas as pd
import boto3
import io
import os
import s3fs
from sqlalchemy import create_engine

import warnings
warnings.filterwarnings('ignore')

# MinIO Configs
MINIO_ENDPOINT = os.getenv('AWS_S3_ENDPOINT', 'http://minio:9000')
MINIO_ACCESS_KEY = os.getenv('AWS_ACCESS_KEY_ID', 'minioadmin')
MINIO_SECRET_KEY = os.getenv('AWS_SECRET_ACCESS_KEY', 'minioadmin')

print("Configurando cliente S3/MinIO...")
s3_client = boto3.client(
    's3', endpoint_url=MINIO_ENDPOINT,
    aws_access_key_id=MINIO_ACCESS_KEY,
    aws_secret_access_key=MINIO_SECRET_KEY,
    region_name='us-east-1'
)"""

code_extract = """# 1. Read from landing-zone
landing_bucket = 'landing-zone'
file_name = 'penguins.csv'

print(f"Extraindo {file_name} da {landing_bucket}...")
response = s3_client.get_object(Bucket=landing_bucket, Key=file_name)
df = pd.read_csv(io.BytesIO(response['Body'].read()))

print(f"Dados extraídos com sucesso! Linhas: {df.shape[0]}")
df.head(3)"""

code_load_parquet = """# 2. Transform to Parquet and Load to 'raw' bucket
# We use s3fs to write Pandas DataFrame directly as Parquet into MinIO
raw_bucket = 'raw'
s3_path = f"s3://{raw_bucket}/penguins/penguins_data.parquet"

print(f"Convertendo para Parquet e salvando no bucket '{raw_bucket}'...")
s3_fs = s3fs.S3FileSystem(
    key=MINIO_ACCESS_KEY,
    secret=MINIO_SECRET_KEY,
    client_kwargs={'endpoint_url': MINIO_ENDPOINT}
)

df.to_parquet(s3_path, filesystem=s3_fs, index=False)
print("Arquivo Parquet salvo com sucesso!")"""

code_trino = """# 3. Represent in Trino (Database Raw, Table Penguins)
from sqlalchemy import text

# Conectando ao Trino via JDBC/SQLAlchemy
trino_engine = create_engine('trino://jovyan@trino:8080/minio')

with trino_engine.connect() as con:
    # Cria o Schema (Database) apontando a location pro S3
    print("Criando Schema 'raw'...")
    con.execute(text("CREATE SCHEMA IF NOT EXISTS minio.raw WITH (location = 's3://raw/')"))
    
    # Para registrar nossa tabela, usamos o pandas to_sql que se integra
    # perfeitamente aos catalogos do Iceberg/Hive para criar e popular!
    print("Registrando e inserindo dados na Tabela 'penguins' dentro do database 'raw'...")
    
    # O comando to_sql sobrescreve na engine Trino e salva em formato columnar Parquet nativamente!
    # Caso já exista, ele deleta e recria.
    df.to_sql('penguins', con=trino_engine, schema='raw', if_exists='replace', index=False, method='multi', chunksize=1000)
    
    print("✅ Tabela minio.raw.penguins registrada e pronta para consultas Analytics!")"""

code_verify = """# 4. Homologação / Teste de Query Analytics
with trino_engine.connect() as con:
    result = con.execute(text("SELECT especies, count(*) as count FROM minio.raw.penguins GROUP BY especies"))
    print("\\nResultado Consulta SQL Direto do Trino:")
    for row in result:
        print(row)"""

nb['cells'] = [
    nbf.v4.new_markdown_cell("# ETL: CSV `landing-zone` ➡️ Parquet `raw` (via Trino)"),
    nbf.v4.new_code_cell(code_intro),
    nbf.v4.new_markdown_cell("## 1. Extract (Extração)"),
    nbf.v4.new_code_cell(code_extract),
    nbf.v4.new_markdown_cell("## 2. Salvar como Parquet Bruto (Raw)"),
    nbf.v4.new_code_cell(code_load_parquet),
    nbf.v4.new_markdown_cell("## 3. Load / Catálogo no Trino (Redshift Simulator)"),
    nbf.v4.new_code_cell(code_trino),
    nbf.v4.new_code_cell(code_verify)
]

with open('/home/felipe/projetos/personal/ifood/pipeline_v3/jupyter/notebooks/ETL_PENGUINS_CSV_TO_PARQUET_TRINO.ipynb', 'w') as f:
    nbf.write(nb, f)

print("ETL Notebook generated successfully!")
