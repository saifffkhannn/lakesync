# Execution Guide: ABAP to Snowflake SQL Conversion

This guide details how to execute rules-based and AI-driven conversions of SAP ABAP files to Snowflake SQL.

---

## 1. Start the Conversion Backend Service

The ABAP converter uses a Flask bridge server to manage conversion requests and upload metadata to Snowflake.

1. Navigate to the ABAP conversion backend directory:
   ```powershell
   cd Conversion_ABAP/backend
   ```
2. Activate your virtual environment and install packages:
   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   pip install -e ".[dev]"
   ```
3. Set up your Snowflake environment variables in a `.env` file (copied from `.env.example`).
4. Start the Flask server:
   ```powershell
   python flask_app.py
   ```
   *This starts the bridge API on `http://127.0.0.1:5000`.*

---

## 2. Execute Batch Conversion via CLI (Command Line)

You can convert folders of ABAP source files using command-line scripts:

### Option A: AI-Driven Cortex Conversion (Requires Snowflake)
Uses Snowflake Cortex AI to translate ABAP files and logs metadata to Snowflake:
```powershell
# Run the powershell wrapper script
.\Conversion_ABAP\convert-ai.ps1 -InputFolder .\Conversion_ABAP\backend\sample_abap -OutputFolder .\Conversion_ABAP\backend\output\ai_converted -Recursive
```

### Option B: Local Rule-Based Conversion (Offline)
Runs locally using regex pattern matching and semantic mapping without sending code to Snowflake:
```powershell
cd Conversion_ABAP/backend
python convert_folder.py .\sample_abap --output-folder .\output\local_converted --recursive
```

---

## 3. Run Conversion via the Web Workspace

1. Start the root orchestrator using `run_lakesync.bat` (which starts the main React UI, API Gateway, Ingestion Backend, and ABAP Backend).
2. Open `http://localhost:5173` and click on **ABAP Translation** in the navigation panel.
3. Drag and drop or upload an ABAP source file.
4. Review the converted Snowflake SQL side-by-side with your original ABAP source.
5. If satisfied, click **Deploy to Snowflake** to execute the generated DDL/DML directly on Snowflake, or click **Download SQL** to save it locally.
