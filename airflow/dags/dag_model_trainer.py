from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta
import yaml
import os

# Definition of the DAG basic args
default_args = {
    'owner': 'squad-data',
    'depends_on_past': False,
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 0,
    'retry_delay': timedelta(minutes=1),
}

def load_contracts_and_train():
    """
    PythonOperator: This runs strictly inside the Airflow Worker context.
    It fetches all the `.yaml` files from S3, parses the model architecture,
    trains, uploads to MLflow, and executes Champion vs Challenger logic.
    """
    import boto3
    import pandas as pd
    import io
    import mlflow
    import mlflow.sklearn
    from sklearn.model_selection import train_test_split
    from sklearn.pipeline import Pipeline
    from sklearn.compose import ColumnTransformer
    from sklearn.preprocessing import StandardScaler, OneHotEncoder
    from sklearn.impute import SimpleImputer
    from sklearn.tree import DecisionTreeClassifier
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import f1_score
    from mlflow.client import MlflowClient
    
    # Airflow Env Binding for libraries inside Docker
    os.environ["AWS_ACCESS_KEY_ID"] = "minioadmin"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "minioadmin"
    os.environ["MLFLOW_S3_ENDPOINT_URL"] = "http://minio:9000"
    mlflow.set_tracking_uri("http://mlflow-server:5000")

    s3_client = boto3.client('s3', endpoint_url='http://minio:9000', aws_access_key_id='minioadmin', aws_secret_access_key='minioadmin', region_name='us-east-1')

    # Detect active contracts in MinIO bucket
    print("Iniciando varredura no Data Lake buscando Manifestos...")
    contracts = s3_client.list_objects_v2(Bucket='model-contracts').get('Contents', [])
    if not contracts:
        print("Nenhum contrato de Engenharia achado no Bucket. Fim da DAG.")
        return
        
    for obj in contracts:
        key = obj['Key']
        print(f"=== Processando Pipeline: {key} ===")
        response_yaml = s3_client.get_object(Bucket='model-contracts', Key=key)
        contract = yaml.safe_load(response_yaml['Body'].read())
        
        model_name = contract['metadata']['name']
        mlflow.set_experiment(model_name)
        
        # 1. Extraction from DWH/Landing-Zone
        print(f"Extraindo dados brutos de: {contract['data']['file_name']}")
        data_resp = s3_client.get_object(Bucket=contract['data']['bucket'], Key=contract['data']['file_name'])
        df = pd.read_csv(io.BytesIO(data_resp['Body'].read())).dropna()
        
        target_col = contract['label']['column']
        y = df[target_col]
        X = df.drop(target_col, axis=1)

        # 2. Dynamic Feature Scoping based on YAML 
        numeric_features = [feat['name'] for feat in contract['features'] if feat['dtype'] in ['float', 'int']]
        categorical_features = [feat['name'] for feat in contract['features'] if feat['dtype'] == 'categorical']

        num_transf = Pipeline(steps=[('imputer', SimpleImputer(strategy='median')), ('scaler', StandardScaler())])
        cat_transf = Pipeline(steps=[('imputer', SimpleImputer(strategy='most_frequent')), ('onehot', OneHotEncoder(handle_unknown='ignore'))])

        preprocessor = ColumnTransformer(transformers=[('num', num_transf, numeric_features), ('cat', cat_transf, categorical_features)])

        # 3. Model Engine parsing
        alg = contract['model']['algorithm']
        params = contract['model']['hyperparameters']
        if alg == 'decision_tree': clf = DecisionTreeClassifier(**params)
        elif alg == 'random_forest': clf = RandomForestClassifier(**params)
        elif alg == 'logistic_regression': clf = LogisticRegression(**params)
        else: raise ValueError("Algoritmo não suportado nesta DAG")

        pipeline = Pipeline(steps=[('preprocessor', preprocessor), ('classifier', clf)])
        X_treino, X_teste, y_treino, y_teste = train_test_split(X, y, test_size=contract['data']['splits']['test'], random_state=42)

        # 4. Actual execution over Tracker Watch 
        with mlflow.start_run(run_name=f"DagExecution_{contract['metadata']['version']}") as run:
            pipeline.fit(X_treino, y_treino)
            previsoes = pipeline.predict(X_teste)
            f1 = f1_score(y_teste, previsoes, average='weighted') if contract['problem']['type'] == 'multiclass_classification' else f1_score(y_teste, previsoes)
            
            mlflow.log_metric(contract['problem']['target_metric'], f1)
            mlflow.log_param("algoritmo_engine", alg)
            mlflow.log_params(params)
            
            mlflow.sklearn.log_model(pipeline, "pipeline_scikit_learn_completo")
            
            # --- CHAMPION vs CHALLENGER TOURNAMENT MATEMATICO ---
            print("--- Iniciando Duelo Shadow / Champion ---")
            client = MlflowClient()
            model_uri = f"runs:/{run.info.run_id}/pipeline_scikit_learn_completo"
            model_details = mlflow.register_model(model_uri=model_uri, name=model_name)
            
            try:
                champion_info = client.get_model_version_by_alias(name=model_name, alias="Champion")
                champion_run = client.get_run(champion_info.run_id)
                f1_campeao = champion_run.data.metrics.get(contract['problem']['target_metric'], 0)
                
                print(f"F1 The King (Atual Produção): {f1_campeao}")
                print(f"F1 The Usurper (Acabou de Treinar): {f1}")
                
                if f1 > f1_campeao:
                     print("🔥 O DESAFIANTE DERRUBOU O CAMPEAO! Deploy liberado para nova subida.")
                     client.set_registered_model_alias(name=model_name, alias="Champion", version=model_details.version)
                     client.set_model_version_tag(name=model_name, version=model_details.version, key="Stage", value="Promoted-via-Airflow-DAG")
                else:
                     print("♻️ O modelo antigo era melhor. Este novo pipeline perderá espaço, apenas será arquivado mas não fará deploy na API.")
                     client.set_registered_model_alias(name=model_name, alias="Challenger", version=model_details.version)
                     client.set_model_version_tag(name=model_name, version=model_details.version, key="Stage", value="Rejected-Bad-Score")
                     
            except Exception as e:
                print("E esse foi o primeirissimo modelo criado no MLflow sem concorrência! Model coroado cego como Campeão Zero.")
                client.set_registered_model_alias(name=model_name, alias="Champion", version=model_details.version)

with DAG(
    'MLOps_Universal_Contract_Pipeline',
    default_args=default_args,
    description='Escaneia Bucket YAML e gerencia ciclo de vida do Campeão. Executada diáriamente às 03:00AM',
    schedule_interval=timedelta(days=1),
    start_date=datetime(2025, 1, 1),
    catchup=False,
    tags=['architecture-as-code', 'mlops', 'contract-driven'],
) as dag:

    model_training_task = PythonOperator(
        task_id='fetch_contracts_and_run_tournaments',
        python_callable=load_contracts_and_train,
    )

    model_training_task
