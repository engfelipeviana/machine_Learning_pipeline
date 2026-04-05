FROM python:3.10-slim

WORKDIR /app

RUN pip install --no-cache-dir \
    boto3 \
    mlflow==2.11.3 \
    scikit-learn \
    pyyaml \
    pandas \
    pyarrow \
    evidently

COPY train.py .
COPY drift_monitor.py .
