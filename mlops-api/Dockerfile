FROM python:3.10-slim

WORKDIR /app

RUN pip install --no-cache-dir \
    fastapi \
    python-multipart \
    uvicorn \
    pydantic \
    mlflow==2.11.3 \
    boto3 \
    pandas \
    scikit-learn

COPY main.py .

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
