# ABAP to Snowflake AI Conversion Platform

This workspace converts SAP ABAP/Open SQL programs into Snowflake SQL artifacts. It includes:

- A folder-based converter for ABAP files.
- A FastAPI backend that uses Snowflake Cortex AI for conversion.
- A React Native frontend in `frontend/` and a Flask bridge API in `backend/flask_app.py`.
- Snowflake infrastructure SQL for storing requests, results, validation history, feedback, and deployments.

## Quick Start: AI Conversion

From the repository root:

```powershell
Copy-Item .\backend\.env.example .\backend\.env
notepad .\backend\.env
```

Fill in the Snowflake values in `backend/.env`, then run:

```powershell
.\convert-ai.ps1 -InputFolder .\backend\sample_abap -OutputFolder .\backend\output\ai_converted -Recursive
```

That command uses `backend/convert_folder.py` with `--upload-snowflake`, which means conversion goes through Snowflake Cortex AI and persists request/result rows in Snowflake.

## Daily Commands

Install backend dependencies:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
```

Run AI conversion:

```powershell
cd "D:\Accelerator\ABAP Conversion"
.\convert-ai.ps1 -InputFolder .\backend\sample_abap -OutputFolder .\backend\output\ai_converted -Recursive
```

Run local non-AI conversion:

```powershell
cd backend
.\.venv\Scripts\python.exe convert_folder.py .\sample_abap --output-folder .\output\local_converted --recursive
```

Start backend API:

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload
```

Start the Flask bridge API:

```powershell
cd backend
python flask_app.py
```

Start the React Native frontend:

```powershell
cd frontend
npm install
npm start
```

Expo will show options for running on web, Android, iOS, or a device. Keep the Flask API running at `http://127.0.0.1:5000`.

Use the UI to:

- Upload an ABAP source file.
- Convert it through `run_conversion` in `backend/convert_folder.py`.
- Review original ABAP and generated Snowflake SQL side by side.
- Optionally upload the displayed SQL to Snowflake before downloading the `.sql` file.

Run backend tests:

```powershell
cd backend
pytest
```

## Repository Layout

- `backend/`: Python FastAPI service, folder CLI, conversion pipeline, Snowflake integration, and tests.
- `backend/app/api/`: HTTP routes for auth, conversion, review, deployment, and system status.
- `backend/app/core/`: app settings, logging, observability, and JWT security.
- `backend/app/schemas/`: Pydantic models used across API, pipeline, validation, and review.
- `backend/app/services/`: parser, rule engine, AI converter, validation, storage, deployment, metadata, feedback memory.
- `backend/sample_abap/`: sample ABAP inputs.
- `backend/output/`: recommended generated output folder.
- `frontend/`: React Native/Expo upload and conversion UI.
- `infra/snowflake/`: Snowflake storage/search setup SQL.
- `infra/kubernetes/`: deployment manifests.
- `docs/PROJECT_STRUCTURE.md`: fuller explanation of how the workspace is organized.

## Snowflake Setup

The AI path requires valid Snowflake credentials and Cortex access. Configure these in `backend/.env`:

```text
SNOWFLAKE_ACCOUNT=
SNOWFLAKE_USER=
SNOWFLAKE_PASSWORD=
SNOWFLAKE_WAREHOUSE=
SNOWFLAKE_DATABASE=
SNOWFLAKE_SCHEMA=
SNOWFLAKE_ROLE=
SNOWFLAKE_DISABLE_PROXY=true
```

Create the storage model through the CLI/API path automatically, or manually run:

```powershell
snowsql -f .\infra\snowflake\001_storage_model.sql
snowsql -f .\infra\snowflake\002_cortex_search.sql
```

## Output Files

Each input ABAP file generates:

- `.sql`: generated Snowflake SQL.
- `.json`: conversion report with confidence, warnings, assumptions, applied rules, AST annotations, dependencies, and memory retrieval details.

Generated files should go under `backend/output/`. Existing evaluation outputs under `backend/eval_*` are kept as historical examples.

## How Snowflake Saves Conversions

API/UI conversion writes records to Snowflake as part of the conversion pipeline:

- `CONVERSION_REQUESTS`: original source name, ABAP source, checksum, detected features, status, and submitter.
- `CONVERSION_RESULTS`: generated SQL, confidence score, artifact type, warnings, assumptions, and conversion notes.
- `VALIDATION_RESULTS`: syntax, object, semantic, query-plan, execution, and confidence validation outcomes.
- `REVIEW_HISTORY`: reviewer approval/edit actions from the UI.
- `FEEDBACK_DATASET`: final reviewer SQL and validation summary for future learning.
- `DEPLOYMENT_RELEASES`: deployed Snowflake artifact versions when an approved conversion is deployed.

Folder conversion only saves to Snowflake when run with the AI flag:

```powershell
.\convert-ai.ps1 -InputFolder .\backend\sample_abap -OutputFolder .\backend\output\ai_converted -Recursive
```
