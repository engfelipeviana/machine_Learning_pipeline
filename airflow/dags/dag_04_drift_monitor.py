from airflow import DAG
from airflow.providers.docker.operators.docker import DockerOperator
from airflow.operators.python import BranchPythonOperator
from airflow.operators.trigger_dagrun import TriggerDagRunOperator
from airflow.operators.empty import EmptyOperator
from datetime import datetime, timedelta

default_args = {
    'owner': 'squad-data',
    'depends_on_past': False,
    'start_date': datetime(2026, 4, 1),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

def parse_drift_xcom(**context):
    # Airflow captura o ultimo print do container docker
    xcom_value = context['ti'].xcom_pull(task_ids='verify_statistical_data_drift')
    if xcom_value and "DRIFT_DETECTED: TRUE" in xcom_value.upper():
        return 'trigger_model_retraining'
    return 'end_monitoring'

with DAG(
    'DAG_04_Drift_Monitor',
    default_args=default_args,
    description='EvidentlyAI Data Drift Monitoring over Production Assets',
    schedule_interval='@weekly',
    catchup=False,
    tags=['mlops', 'evidently', 'drift', 'monitoring'],
) as dag:

    monitor_drift = DockerOperator(
        task_id='verify_statistical_data_drift',
        image='worker-mlops:latest',
        container_name='airflow-drift-worker-{{ ts_nodash }}',
        api_version='auto',
        auto_remove=True,
        docker_url='unix://var/run/docker.sock',
        network_mode='mlops-net',
        command='python drift_monitor.py',
        mount_tmp_dir=False,
        do_xcom_push=True,
        environment={
            'MLFLOW_S3_ENDPOINT_URL': 'http://minio:9000',
            'AWS_ACCESS_KEY_ID': 'minioadmin',
            'AWS_SECRET_ACCESS_KEY': 'minioadmin'
        }
    )

    branch_task = BranchPythonOperator(
        task_id='check_drift_threshold',
        python_callable=parse_drift_xcom,
    )

    trigger_retrain = TriggerDagRunOperator(
        task_id='trigger_model_retraining',
        trigger_dag_id='DAG_02_Model_Trainer',
        wait_for_completion=False,
    )

    end = EmptyOperator(task_id='end_monitoring')

    monitor_drift >> branch_task >> [trigger_retrain, end]
