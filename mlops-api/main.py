import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import mlflow
import pandas as pd

# Definindo logs profissionais
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Resgatando chaves do Cluster Docker
MLFLOW_S3_ENDPOINT_URL = os.environ.get('MLFLOW_S3_ENDPOINT_URL', "http://minio:9000")
MLFLOW_TRACKING_URI = os.environ.get('MLFLOW_TRACKING_URI', "http://mlflow-server:5000")
os.environ['AWS_ACCESS_KEY_ID'] = os.environ.get('AWS_ACCESS_KEY_ID', 'minioadmin')
os.environ['AWS_SECRET_ACCESS_KEY'] = os.environ.get('AWS_SECRET_ACCESS_KEY', 'minioadmin')

mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)

# Dicionário de estado do backend para armazenar o Modelo Permanente (Single-Pass Load RAM)
app_state = {}

@asynccontextmanager
async def lifespan(app: FastAPI):
    # STARTUP
    logger.info("📡 Inicializando microserviço FastAPI e comunicando-se com MLflow...")
    
    model_name = "penguins_classification_v1"
    alias = "Champion"
    
    try:
        # Resolve via MLflow native API o artefato exato escondido dentro da camada `@Champion`
        model_uri = f"models:/{model_name}@{alias}"
        logger.info(f"💾 Baixando e injetando o modelo ({model_uri}) na Memória RAM...")
        
        champion_model = mlflow.sklearn.load_model(model_uri)
        app_state["model"] = champion_model
        logger.info("🚀 Modelo @Champion pronto para inferência assíncrona!")
        
    except Exception as e:
        logger.error(f"❌ Falha crítica ao puxar o modelo: {str(e)}")
        app_state["model"] = None
        
    yield
    
    # SHUTDOWN
    app_state.clear()
    logger.info("Serviço de Inferência Desligado.")

# Rotas Web
app = FastAPI(
    title="MLOps Prediction Engine API",
    description="Endpoint assíncrono hiper-rápido para classificar solicitações via modelo Champion do Airflow.",
    version="1.0.0",
    lifespan=lifespan
)

# Validação rígida Pydantic dos features da RAW Layer
class PenguinFeatures(BaseModel):
    ilha: str
    bico_comp_mm: float
    bico_largura_mm: float
    nadadeira_comp_mm: float
    masso_corporal_g: float
    sexo: str

@app.get("/health")
def health_check():
    status = "healthy" if app_state.get("model") is not None else "degraded"
    return {"status": status, "model_loaded": status == "healthy"}

@app.post("/predict")
async def predict_species(features: PenguinFeatures):
    model = app_state.get("model")
    if model is None:
        raise HTTPException(status_code=503, detail="Modelo @Champion não está disponível na RAM. O MLflow pode estar inacessível.")
    
    try:
        # Cast transparente do Payload JSON para DataFrame (Para o Pickle entender a Transformação do Pipeline)
        data_df = pd.DataFrame([features.dict()])
        
        # O Scikit-Learn Pipeline executa OHE (One-Hot-Encoding) e Imputers automaticamente baseado nas matrizes congeladas da DAG 2
        prediction = model.predict(data_df)
        
        return {"Especie Prevista": str(prediction[0])}
        
    except Exception as e:
        logger.error(f"Erro em Predict: {e}")
        raise HTTPException(status_code=500, detail=str(e))
