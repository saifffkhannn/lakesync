import os
import sys
import json

# Add project root to sys.path
BASE_DIR = r"d:\Accelerator\Data Migration\Incremental_Load\ingestion_engine"
sys.path.append(BASE_DIR)

from backend_helper import BackendHelper

CONFIG_PATH = os.path.join(BASE_DIR, "config", "config.json")
backend = BackendHelper(CONFIG_PATH)

try:
    columns = backend.get_source_metadata(schema_name="Sales", table_name="Customers", action="columns")
    print(json.dumps(columns, indent=2))
except Exception as e:
    print(f"Error: {e}")
