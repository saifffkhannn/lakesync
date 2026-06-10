# Execution Guide: Data Load Ingestion (Full & Incremental)

This guide provides instructions on starting and running the Full and Incremental (CDC) data loading pipelines.

---

## 1. Start the Ingestion Backend Service

The Ingestion Engine is built using FastAPI. 

1. Open a terminal and navigate to the ingestion engine folder:
   ```powershell
   cd ingestion_engine
   ```
2. Activate your virtual environment and install dependencies:
   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   ```
3. Start the FastAPI application on port `8001`:
   ```powershell
   uvicorn api:app --port 8001
   ```

---

## 2. Start the Frontend UI

1. Open a new terminal and navigate to the frontend folder:
   ```powershell
   cd lakesync
   ```
2. Install dependencies (if not done already):
   ```powershell
   npm install
   ```
3. Start the Vite React development server:
   ```powershell
   npm run dev
   ```
   *The interface will run on `http://localhost:5173`.*

---

## 3. Run Ingestion via the Web Interface

1. Navigate to the dashboard at `http://localhost:5173`.
2. Click on **New Ingestion** or navigate to the connection wizard page.
3. Fill in your **Source Database Credentials** (e.g. SAP SQL Server).
4. Fill in your **Cloud Staging Configuration** (S3 Bucket & AWS credentials).
5. Fill in your **Target Data Warehouse Credentials** (Snowflake or Databricks).
6. Click **Save Configuration** and click **Go To Source Mapper**.
7. In the Source Mapper:
   - Select the target database schema.
   - Map columns, select primary keys, and identify a watermark column (e.g. `LastModifiedDate`) for incremental CDC updates.
8. Click **Start Ingestion** to trigger the pipeline.
9. Monitor the progress bars and logs on the **Pipeline Status** screen.

---

## 4. Run/Test Ingestion via Automation CLI Script

To run a headless test migration without using the UI:
1. Ensure the backend FastAPI service is running on port `8001`.
2. Execute the migration testing script:
   ```powershell
   python ingestion_engine/scratch/test_migration.py
   ```
   *This script posts the JSON configuration payload, configures mappings, triggers extraction, and polls the pipeline status endpoints until completion.*
