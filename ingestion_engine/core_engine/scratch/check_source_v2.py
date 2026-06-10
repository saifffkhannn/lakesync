import pyodbc
import pandas as pd
import configparser

config = configparser.ConfigParser()
config.read("config/sapsqlserver_aws_snowflake.cfg")

conn_str = (
    f"DRIVER={{ODBC Driver 17 for SQL Server}};"
    f"SERVER={config['sapsqlserver']['server_name']};"
    f"DATABASE={config['sapsqlserver']['database']};"
    f"UID={config['sapsqlserver']['user']};"
    f"PWD={config['sapsqlserver']['password']};"
)

conn = pyodbc.connect(conn_str)

print("--- Customers ---")
query = "SELECT MAX(LastUpdatedAt) as max_last_upd, COUNT(*) as cnt FROM Sales.Customers"
print(pd.read_sql(query, conn))

print("\n--- Orders ---")
query = "SELECT MAX(LastUpdatedAt) as max_last_upd, COUNT(*) as cnt FROM Sales.Orders"
print(pd.read_sql(query, conn))

print("\n--- Sample Rows (Customers) ---")
print(pd.read_sql("SELECT TOP 5 * FROM Sales.Customers ORDER BY LastUpdatedAt DESC", conn))

conn.close()
