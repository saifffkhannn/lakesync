# LakeSync & Data Load Accelerator Platform

A unified, high-performance data engineering platform for enterprise migration, schema conversion, and master data unification. 

---

## 🚀 Architecture & Features

This platform integrates four core capabilities into a single, cohesive workflow:

1. **Full Data Load**: High-throughput extraction of schema metadata and data from operational databases (SAP SQL Server, Oracle, MySQL, Teradata), staging them as optimized Parquet files, and uploading them to cloud storage (AWS S3) to ingest directly into cloud data warehouses (Snowflake, Databricks).
2. **Incremental Data Load (CDC)**: Continuous change-data-capture mapping that monitors, retrieves, and processes incremental changes from source tables, keeping target warehouse tables automatically synchronized.
3. **ABAP to Snowflake SQL Conversion**: An intelligent transpiler that converts legacy SAP ABAP and Open SQL code into native Snowflake SQL using either local rule-based parsing or Snowflake Cortex AI.
4. **Master Data Management (MDM)**: A deduplication and entity unification engine executing within Snowflake (via Snowpark Python and stored procedures). It links multi-source records using fuzzy string-matching rules to produce a single, consolidated master record.

---

## 🗺️ Project Layout

```
DATA LOAD ACCELERATORS/
├── lakesync/               # React (Vite) Frontend UI for dashboards & configurations
├── Ingestion_engine/       # FastAPI Backend for Full/Incremental load pipelines & API gateway bridge
├── Conversion_ABAP/        # Flask Backend & CLI scripts for ABAP-to-Snowflake SQL conversion
├── mdm/                    # Modular MDM engine (Connection, Schema, Procedures, Queries, Runner)
├── api_gateway.py          # Unified Router/Gateway handling incoming frontend API calls
├── run_lakesync.bat        # Automated orchestrator script to spin up the entire local stack
├── test/                   # (Ignored) Archive folder containing unused references and slides
└── .gitignore              # Configured Git ignore file to shield secrets (*.cfg, config.json)
```

---

## ⚡ Quick Start: Running the Platform

All microservices are bound together by an automated starter script. Follow the steps below to spin up the development environment.

### 1. Prerequisites
- **Node.js** (v18+) and **npm**
- **Python** (v3.10 or v3.11) with `pip`
- (Optional) **Snowflake Account** and credentials to run ABAP conversions via Cortex AI or MDM unification pipelines.

For detailed module-specific configuration requirements, see:
- 📊 **[Data Load Prerequisites](file:///d:/DATA%20LOAD%20ACCELERATORS/docs/prerequisites_dataload.md)**
- ⚙️ **[ABAP Conversion Prerequisites](file:///d:/DATA%20LOAD%20ACCELERATORS/docs/prerequisites_abap.md)**
- 🔄 **[Master Data Management (MDM) Prerequisites](file:///d:/DATA%20LOAD%20ACCELERATORS/docs/prerequisites_mdm.md)**

### 2. Set Up Configuration (Optional)
Configure Snowflake/Cloud credentials inside the `.env` or configuration templates if you wish to run live cloud pipelines. Check:
- `Conversion_ABAP/backend/.env` (based on `Conversion_ABAP/backend/.env.example`)
- Connection settings inside the UI configuration forms.

### 3. Launch the Stack
Double-click or run the orchestrator script from the root of the workspace:

```powershell
.\run_lakesync.bat
```

This script will automatically:
1. Start the **Ingestion Backend** on port `8001`.
2. Start the **ABAP Conversion Backend** on port `5000`.
3. Launch the **API Gateway** on port `8000`.
4. Spin up the **Vite React Frontend** on port `5173`.
5. Open your default web browser to the dashboard at [http://localhost:5173](http://localhost:5173).

---

## ⚙️ Service Ports Reference

| Service | Port | Directory | Run Command |
| :--- | :--- | :--- | :--- |
| **API Gateway** | `8000` | `/` | `python api_gateway.py` |
| **Ingestion Engine** | `8001` | `/ingestion_engine` | `uvicorn api:app --port 8001` |
| **ABAP Backend** | `5000` | `/Conversion_ABAP/backend` | `python flask_app.py` |
| **Frontend UI** | `5173` | `/lakesync` | `npm run dev` |

---

## 🔄 Pipeline Workflows

### Full & Incremental Load Ingestion
1. Define source databases, cloud staging storage (S3), and destination credentials in the Frontend UI.
2. Select target tables and define primary keys/watermark columns for incremental synchronization.
3. Track real-time progress cards and pipeline ingestion logs on the dashboard.

### ABAP Conversion
1. Upload `.txt` or `.abap` files directly in the conversion panel.
2. The backend parses code structure and translates Open SQL statements to Snowflake syntax.
3. Compare source ABAP code and generated SQL side-by-side with confidence metrics, warnings, and target mappings.

### Master Data Management (MDM)
1. Mapping configs stage source databases to Bronze schema targets using change tracking.
2. Snowflake streams capture inputs, triggering `SP_LOAD_GROUP` and Snowpark's `SP_MASTER_ENTITY`.
3. Records are clustered, matched against existing master identifiers using similarity algorithms, and flattened into the `MASTER_ENTITY_FLAT` view.

---

## 📖 Module Run & Execution Guides

For step-by-step instructions on running each module independently or via the CLI interfaces, consult the execution guides:
- 📊 **[Data Ingestion Data Flow Guide](file:///d:/DATA%20LOAD%20ACCELERATORS/docs/data_flow_ingestion.md)**
- ⚙️ **[ABAP Conversion Data Flow Guide](file:///d:/DATA%20LOAD%20ACCELERATORS/docs/data_flow_abap.md)**
- 🔄 **[Master Data Management Data Flow Guide](file:///d:/DATA%20LOAD%20ACCELERATORS/docs/data_flow_mdm.md)**
- 📊 **[Data Load Run Guide](file:///d:/DATA%20LOAD%20ACCELERATORS/docs/run_dataload.md)**
- ⚙️ **[ABAP Conversion Run Guide](file:///d:/DATA%20LOAD%20ACCELERATORS/docs/run_abap.md)**
- 🔄 **[Master Data Management (MDM) Run Guide](file:///d:/DATA%20LOAD%20ACCELERATORS/docs/run_mdm.md)**
