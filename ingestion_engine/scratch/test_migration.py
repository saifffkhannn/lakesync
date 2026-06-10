import time
import requests
import json

base_url = "http://localhost:8000"

# Load credentials/config from the UI dev_config
config_data = {
  "source": {
    "server_name": "DESKTOP-JLOBD2O\\SQLEXPRESS",
    "database": "bikestores",
    "user": "sa",
    "password": "synthlake@1",
    "platform": "SAPSQLServer"
  },
  "target": {
    "account": "BYVCTSJ-CVB58275",
    "user": "SAIADITHYA",
    "password": "Synthlake@2026",
    "warehouse": "COMPUTE_WH",
    "stage_name": "bikestores_stg",
    "stage_schema": "bikestores_stg",
    "database": "bikestores",
    "platform": "Snowflake"
  },
  "cloud": {
    "aws_region": "eu-north-1",
    "aws_access_key_id": "YOUR_AWS_ACCESS_KEY_ID",
    "aws_secret_access_key": "YOUR_AWS_SECRET_ACCESS_KEY",
    "s3_bucket_name": "stageddataparqe",
    "base_path": "s3://stageddataparqe/",
    "platform": "AWS"
  },
  "load_type": "FULL"
}

def wait_for_pipeline():
    print("Waiting for migration pipeline to complete...")
    while True:
        try:
            r = requests.get(f"{base_url}/migration-status")
            status_data = r.json()
            progress = status_data.get("progress", 0)
            table_statuses = status_data.get("table_status", [])
            print(f"Progress: {progress}%")
            
            # Print last few logs if available
            logs = status_data.get("logs", [])
            if logs:
                print(f"Last log: {logs[-1]}")
                
            completed = True
            failed = False
            for ts in table_statuses:
                status = ts.get("status", "").lower()
                if status in ["pending", "extracting", "extracted", "uploading", "uploaded", "creating_table", "loading"]:
                    completed = False
                elif "failed" in status:
                    failed = True
            
            if failed:
                print("Pipeline failed!")
                print(json.dumps(table_statuses, indent=2))
                return False
            if completed and progress == 100:
                print("Pipeline finished successfully!")
                print(json.dumps(table_statuses, indent=2))
                return True
        except Exception as e:
            print("Error polling status:", e)
        time.sleep(5)

def run_flow():
    # 1. Save Config (Full Load)
    print("1. Saving config for FULL load...")
    config_data["load_type"] = "FULL"
    r = requests.post(f"{base_url}/config", json=config_data)
    print("Response:", r.json())
    
    # 2. Save Credentials too just in case
    print("Saving credentials configuration...")
    creds_payload = {
        "source": "SAPSQLServer",
        "cloud": "AWS",
        "target": "Snowflake",
        "data": {
            "sapsqlserver": config_data["source"],
            "snowflake": config_data["target"],
            "aws": config_data["cloud"]
        }
    }
    r = requests.post(f"{base_url}/save-credentials", json=creds_payload)
    print("Response:", r.json())
    
    # 3. Save Column Mappings and Watermark Column Selection
    print("3. Saving column mappings and watermark for production.brands...")
    mapping_payload = [
        {
            "src_db": "bikestores",
            "src_schema": "production",
            "src_table": "brands",
            "tgt_db": "bikestores",
            "tgt_schema": "production",
            "tgt_table": "brands",
            "column_map": {
                "brand_id": "brand_id",
                "brand_name": "brand_name",
                "LastModifiedDate": "LastModifiedDate"
            },
            "source_columns": ["brand_id", "brand_name", "LastModifiedDate"],
            "target_columns": ["brand_id", "brand_name", "LastModifiedDate"],
            "incremental_src_col": "LastModifiedDate",
            "primary_keys": ["brand_id"]
        }
    ]
    r = requests.post(f"{base_url}/mapping/batch", json=mapping_payload)
    print("Response:", r.json())
    
    # 4. Start full load extraction migration
    print("4. Starting FULL LOAD extraction...")
    extract_payload = {
        "source": "SAPSQLServer",
        "cloud": "AWS",
        "target": "Snowflake",
        "metadata_filename": "sapsqlserver_metadata.csv"
    }
    r = requests.post(f"{base_url}/start-extraction", json=extract_payload)
    print("Response:", r.json())
    
    # 5. Wait for Full Load completion
    if not wait_for_pipeline():
        print("Full load pipeline failed. Exiting.")
        return
        
    # 6. Save Config for Incremental Load
    print("\n5. Saving config for INCREMENTAL load...")
    config_data["load_type"] = "INCREMENTAL"
    r = requests.post(f"{base_url}/config", json=config_data)
    print("Response:", r.json())
    
    # 7. Start incremental load ingestion
    print("6. Starting INCREMENTAL LOAD ingestion...")
    r = requests.post(f"{base_url}/ingest")
    print("Response:", r.json())
    
    # 8. Wait for Incremental completion
    print("Waiting for incremental ingestion to complete...")
    while True:
        try:
            r = requests.get(f"{base_url}/ingest/status")
            status_data = r.json()
            status = status_data.get("status", "").upper()
            progress = status_data.get("progress", 0)
            print(f"Status: {status}, Progress: {progress}%")
            
            if status == "COMPLETED":
                print("Incremental load completed successfully!")
                print(json.dumps(status_data.get("details", []), indent=2))
                break
            elif status == "FAILED":
                print("Incremental load failed!")
                print(json.dumps(status_data.get("details", []), indent=2))
                break
        except Exception as e:
            print("Error polling status:", e)
        time.sleep(5)

if __name__ == "__main__":
    run_flow()
