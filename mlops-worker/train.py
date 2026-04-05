import argparse
import boto3
import pandas as pd
import io
import mlflow
import mlflow.sklearn
import os
import yaml
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

def train_contract(contract_key):
    s3_endpoint = os.environ.get("MLFLOW_S3_ENDPOINT_URL", "http://minio:9000")
    mlflow.set_tracking_uri(os.environ.get("MLFLOW_TRACKING_URI", "http://mlflow-server:5000"))

    s3_client = boto3.client('s3', endpoint_url=s3_endpoint, region_name='us-east-1')

    print(f"=== Worker Iniciado para Processar Pipeline: {contract_key} ===")
    response_yaml = s3_client.get_object(Bucket='model-contracts', Key=contract_key)
    contract = yaml.safe_load(response_yaml['Body'].read())
    
    model_name = contract['metadata']['name']
    mlflow.set_experiment(model_name)
    
    print(f"Extraindo features curadas da Feature Store Offline (Iceberg/Trusted Layer)...")
    table_name = contract['data']['file_name'].replace('.csv', '')
    data_resp = s3_client.get_object(Bucket='trusted', Key=f"{table_name}/{table_name}_trusted.parquet")
    df = pd.read_parquet(io.BytesIO(data_resp['Body'].read()))
    
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
    with mlflow.start_run(run_name=f"WorkerExecution_{contract['metadata']['version']}") as run:
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
            
            if f1 >= f1_campeao:
                 print("O DESAFIANTE EMPATOU OU DERRUBOU O CAMPEAO! Deploy liberado para nova subida.")
                 client.set_registered_model_alias(name=model_name, alias="Champion", version=model_details.version)
                 client.set_model_version_tag(name=model_name, version=model_details.version, key="Stage", value="Promoted-via-Airflow-Worker")
            else:
                 print("O modelo antigo era melhor. Este novo pipeline perderá espaço, apenas será arquivado mas não fará deploy na API.")
                 client.set_registered_model_alias(name=model_name, alias="Challenger", version=model_details.version)
                 client.set_model_version_tag(name=model_name, version=model_details.version, key="Stage", value="Rejected-Bad-Score")
                 
        except Exception as e:
            print("E esse foi o primeirissimo modelo criado no MLflow sem concorrência! Model coroado cego como Campeão Zero.")
            client.set_registered_model_alias(name=model_name, alias="Champion", version=model_details.version)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='MLOps Worker Trainer')
    parser.add_argument('--contract', type=str, required=True, help='Nome do contrato YAML no MinIO')
    args = parser.parse_args()
    
    train_contract(args.contract)
