import os
import sys
import json
import configparser

# Add project root to sys.path
BASE_DIR = r"d:\Accelerator\Data Migration\Incremental_Load\ingestion_engine"
sys.path.append(BASE_DIR)

from backend_helper import BackendHelper
from src.connections import get_Source_connection

CONFIG_PATH = os.path.join(BASE_DIR, "config", "config.json")
backend = BackendHelper(CONFIG_PATH)
cfg_path, source_type, _, _ = backend.create_temp_cfg()

conn = get_Source_connection(cfg_path, source_type)
cursor = conn.cursor()
cursor.execute("SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = 'Sales' AND TABLE_NAME = 'Customers'")
rows = cursor.fetchall()
print("Raw columns:", [row[0] for row in rows])
conn.close()
