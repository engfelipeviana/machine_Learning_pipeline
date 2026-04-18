import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Form
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings
import mlflow
import pandas as pd

# Definindo logs profissionais
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Resgatando chaves do Cluster Docker com tipagem forte e validação (Pydantic Settings)
class Settings(BaseSettings):
    mlflow_s3_endpoint_url: str = "http://minio:9000"
    mlflow_tracking_uri: str = "http://mlflow-server:5000"
    aws_access_key_id: str = "minioadmin"
    aws_secret_access_key: str = "minioadmin"

settings = Settings()

os.environ['MLFLOW_S3_ENDPOINT_URL'] = settings.mlflow_s3_endpoint_url
os.environ['AWS_ACCESS_KEY_ID'] = settings.aws_access_key_id
os.environ['AWS_SECRET_ACCESS_KEY'] = settings.aws_secret_access_key

mlflow.set_tracking_uri(settings.mlflow_tracking_uri)

# Dicionário de estado do backend para armazenar o Modelo Permanente (Single-Pass Load RAM)
app_state = {}

@asynccontextmanager
async def lifespan(app: FastAPI):
    # STARTUP
    logger.info("Inicializando microserviço FastAPI e comunicando-se com MLflow...")
    
    model_name = "insurance_regression_v1"
    alias = "Champion"
    
    try:
        # Resolve via MLflow native API o artefato exato escondido dentro da camada `@Champion`
        model_uri = f"models:/{model_name}@{alias}"
        logger.info(f"Baixando e injetando o modelo ({model_uri}) na Memória RAM...")
        
        champion_model = mlflow.sklearn.load_model(model_uri)
        app_state["model"] = champion_model
        logger.info("Modelo @Champion pronto para inferência assíncrona!")
        
    except Exception as e:
        logger.error(f"Falha crítica ao puxar o modelo: {str(e)}")
        app_state["model"] = None
        
    yield
    
    # SHUTDOWN
    app_state.clear()
    logger.info("Serviço de Inferência Desligado.")

# Rotas Web
app = FastAPI(
    title="MLOps Prediction Engine API",
    description="Endpoint de inferência para prever o custo de seguro de saúde via modelo Champion do Airflow.",
    version="2.0.0",
    lifespan=lifespan
)

# Validação rígida Pydantic dos features da RAW Layer
class InsuranceFeatures(BaseModel):
    age: int
    bmi: float
    children: int
    sex: str
    smoker: str
    region: str

@app.get("/health")
def health_check():
    status = "healthy" if app_state.get("model") is not None else "degraded"
    return {"status": status, "model_loaded": status == "healthy"}

class InsuranceResponse(BaseModel):
    charges_predicted: float

@app.post("/predict", response_model=InsuranceResponse)
def predict_charges(payload: InsuranceFeatures):
    model = app_state.get("model")
    if model is None:
        raise HTTPException(status_code=503, detail="Modelo @Champion não disponível na RAM.")
    
    try:
        payload_dict = payload.model_dump()
        # Cast transparente do Form para DataFrame
        data_df = pd.DataFrame([payload_dict])
        
        # Predição com o Pipeline do Scikit-Learn
        prediction = model.predict(data_df)
        
        return {"charges_predicted": float(prediction[0])}
        
    except Exception as e:
        logger.error(f"Erro em Predict: {e}")
        raise HTTPException(status_code=500, detail=str(e))