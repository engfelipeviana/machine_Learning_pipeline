from trino.dbapi import connect
import pandas as pd

# Connect to Trino (Redshift simulator)
conn = connect(
    host="trino",
    port=8080,
    user="jovyan",
    catalog="minio",
    schema="default"
)

cur = conn.cursor()

# Execute a query
cur.execute("SHOW CATALOGS")
print("Catalogs:", cur.fetchall())

# Create a schema in our icebeg catalog if it doesn't exist
cur.execute("CREATE SCHEMA IF NOT EXISTS minio.default WITH (location = 's3a://warehouse/')")

# Create a table from the S3 file we uploaded
# NOTE: Iceberg tables need to be created with properties.
# Or if we just want to query raw files, Hive connector is slightly easier,
# but we can also use Iceberg's "CREATE TABLE AS".
print("Connection to Trino successful.")
