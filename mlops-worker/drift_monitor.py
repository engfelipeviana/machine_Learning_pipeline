import os
import io
import boto3
import yaml
import pandas as pd
from evidently.report import Report
from evidently.metric_preset import DataDriftPreset

print("[INFO] Bootstrapping Drift Monitoring Engine...")

s3_endpoint = os.environ.get("MLFLOW_S3_ENDPOINT_URL", "http://minio:9000")
aws_access_key_id = os.environ.get("AWS_ACCESS_KEY_ID", "minioadmin")
aws_secret_access_key = os.environ.get("AWS_SECRET_ACCESS_KEY", "minioadmin")

s3_client = boto3.client(
    's3', 
    endpoint_url=s3_endpoint, 
    region_name='us-east-1',
    aws_access_key_id=aws_access_key_id,
    aws_secret_access_key=aws_secret_access_key
)

# 1. Carrega Contrato
print("[INFO] Reading Model Contract...")
response_yaml = s3_client.get_object(Bucket='model-contracts', Key='penguins_contract.yaml')
contract = yaml.safe_load(response_yaml['Body'].read())

# 2 & 3. Consumindo Tudo da Trusted (Medallion Compartilhada)
table_name = contract['data']['file_name'].replace('.csv', '')
print(f"[INFO] Pulling Appended Production DataFrame from Iceberg (trusted/{table_name}_trusted.parquet)...")
resp_curr = s3_client.get_object(Bucket='trusted', Key=f"{table_name}/{table_name}_trusted.parquet")
full_data = pd.read_parquet(io.BytesIO(resp_curr['Body'].read()))

if 'ingestion_date' not in full_data.columns:
    print("[WARNING] Ingestion date metadata not found. Defaulting to full comparison.")
    reference_data = full_data
    current_data = full_data
else:
    # Trata dados legados da Fase 1 que não tinham data de ingestão (NaT)
    full_data['ingestion_date'] = pd.to_datetime(full_data['ingestion_date']).fillna(pd.Timestamp("2000-01-01"))
    
    # Separa Base Histórica (Tudo antes da ultima carga) vs Base Nova (Ultima Carga)
    full_data = full_data.sort_values(by='ingestion_date')
    dates = full_data['ingestion_date'].unique()
    
    if len(dates) > 1:
        latest_date = dates[-1]
        reference_data = full_data[full_data['ingestion_date'] != latest_date].drop(columns=['ingestion_date'])
        current_data = full_data[full_data['ingestion_date'] == latest_date].drop(columns=['ingestion_date'])
        print(f"[INFO] Temporal Splitting Sucessful. Reference Window: Historical. Current Window: {latest_date}")
    else:
        print("[WARNING] Only 1 ingestion window found. Cannot compute drift against history.")
        reference_data = full_data.drop(columns=['ingestion_date'])
        current_data = full_data.drop(columns=['ingestion_date'])

# Filter only the valid features recognized by the ML Model logic
features_list = [f['name'] for f in contract['features']]
reference_data = reference_data[features_list]
current_data = current_data[features_list]

# 4. Evidently Report Generation
print("[INFO] Executing Statistical Drift Models over Matrices (Kolmogorov-Smirnov & Wasserstein Distance)...")
report = Report(metrics=[DataDriftPreset()])
report.run(reference_data=reference_data, current_data=current_data)

# 5. Export and Save to MinIO MLOps Repository
html_buffer = io.StringIO()
report.save_html(html_buffer)

# Verify if reports bucket exists
try:
    s3_client.head_bucket(Bucket="mlops-reports")
except:
    s3_client.create_bucket(Bucket="mlops-reports")

s3_client.put_object(
    Bucket='mlops-reports',
    Key=f'{table_name}_drift_report_latest.html',
    Body=html_buffer.getvalue().encode('utf-8'),
    ContentType='text/html'
)

print(f"[SUCCESS] Drift Report HTML rendered and persisted to: s3://mlops-reports/{table_name}_drift_report_latest.html")

# Auto-Trigger Analytics
try:
    report_dict = report.as_dict()
    is_drifted = report_dict["metrics"][0]["result"]["dataset_drift"]
    if is_drifted:
        print("DRIFT_DETECTED: TRUE")
    else:
        print("DRIFT_DETECTED: FALSE")
except Exception as e:
    print(f"Error parsing Evildently JSON: {e}")
    print("DRIFT_DETECTED: FALSE")
