FROM python:3.10-slim

WORKDIR /app

RUN pip install --no-cache-dir \
    pandas \
    boto3 \
    s3fs \
    sqlalchemy \
    trino[sqlalchemy] \
    pyyaml \
    pyarrow

COPY process_data.py .

ENTRYPOINT ["python", "process_data.py"]
