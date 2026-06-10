import snowflake.connector
import json
import os

def run():
    base_dir = r"d:\DATA LOAD ACCELERATORS\ingestion_engine"
    config_path = os.path.join(base_dir, "config", "config.json")
    with open(config_path, "r") as f:
        cfg = json.load(f)
    
    tgt = cfg["target"]
    print("Connecting to Snowflake...")
    conn = snowflake.connector.connect(
        account=tgt["account"],
        user=tgt["user"],
        password=tgt["password"],
        warehouse=tgt["warehouse"]
    )
    cursor = conn.cursor()
    try:
        print("Creating database bikestores if not exists...")
        cursor.execute("CREATE DATABASE IF NOT EXISTS bikestores")
        print("Creating schema production inside bikestores...")
        cursor.execute("CREATE SCHEMA IF NOT EXISTS bikestores.production")
        print("Creating table brands inside bikestores.production...")
        cursor.execute("CREATE TABLE IF NOT EXISTS bikestores.production.brands (brand_id INT, brand_name VARCHAR, LastModifiedDate TIMESTAMP)")
        print("Done!")
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    run()
