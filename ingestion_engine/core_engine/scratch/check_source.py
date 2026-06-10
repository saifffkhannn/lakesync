import pyodbc
import pandas as pd
from src.parse_config import parse_config
import os

base_dir = os.path.dirname(os.path.abspath(__file__))
config_path = os.path.join(base_dir, "config", "sapsqlserver_aws_snowflake.cfg")
config = parse_config(config_path)

conn_str = (
    f"DRIVER={{ODBC Driver 17 for SQL Server}};"
    f"SERVER={config['sapsqlserver']['server_name']};"
    f"DATABASE={config['sapsqlserver']['database']};"
    f"UID={config['sapsqlserver']['user']};"
    f"PWD={config['sapsqlserver']['password']};"
)

conn = pyodbc.connect(conn_str)
query = "SELECT MAX(LastUpdatedAt) as max_val, COUNT(*) as cnt FROM Sales.Customers"
df = pd.read_sql(query, conn)
print("Customers Info:")
print(df)

query = "SELECT MAX(LastUpdatedAt) as max_val, COUNT(*) as cnt FROM Sales.Orders"
df = pd.read_sql(query, conn)
print("\nOrders Info:")
print(df)

conn.close()
