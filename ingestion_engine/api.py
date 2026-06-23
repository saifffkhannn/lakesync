import json
import csv
import os
import logging
import traceback
import sys
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any, Optional

# Add backend to path to import pipeline state
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_ROOT = os.path.join(BASE_DIR, "core_engine")
if BACKEND_ROOT not in sys.path:
    sys.path.append(BACKEND_ROOT)

from backend_helper import BackendHelper
from src.pipeline_state_manager import get_pipeline_snapshot, reset_pipeline_state

logger = logging.getLogger("data_accelerator")
logging.basicConfig(level=logging.INFO)

app = FastAPI()

@app.get("/")
def home():
    return {
        "status": "success",
        "message": "LakeSync API is running!",
        "docs": "/docs"
    }


# Enable CORS for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

CONFIG_PATH = os.path.join(BASE_DIR, "config", "config.json")
backend = BackendHelper(CONFIG_PATH)

class Config(BaseModel):
    source: Dict[str, Any]
    target: Dict[str, Any]
    cloud: Dict[str, Any]
    load_type: Optional[str] = "INCREMENTAL"


@app.get("/config")
def get_config():
    if not os.path.exists(CONFIG_PATH):
        return {}
    with open(CONFIG_PATH, "r") as f:
        return json.load(f)

@app.post("/config")
def save_config(config: Config):
    config_dict = config.model_dump()
    
    os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
    with open(CONFIG_PATH, "w") as f:
        json.dump(config_dict, f, indent=2)
    
    # Generate the backend .cfg file immediately
    backend.create_temp_cfg(config_dict)
    return {"status": "success"}

@app.get("/source/schemas")
def get_source_schemas():
    try:
        return backend.get_source_metadata(action="schemas")
    except Exception as e:
        logger.error(f"Failed to fetch source schemas: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/source/tables")
def get_source_tables(schema: str):
    try:
        return backend.get_source_metadata(schema_name=schema, action="tables")
    except Exception as e:
        logger.error(f"Failed to fetch source tables: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/source/columns")
def get_source_columns(schema: str, table: str):
    try:
        return backend.get_source_metadata(schema_name=schema, table_name=table, action="columns")
    except Exception as e:
        logger.error(f"Failed to fetch source columns: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/target/schemas")
def get_target_schemas():
    try:
        return backend.get_target_metadata(action="schemas")
    except Exception as e:
        err_str = str(e).lower()
        if "does not exist" in err_str or "not authorized" in err_str:
            # Target database not yet created — return empty list so UI can still proceed
            logger.warning(f"Target database not accessible yet (may be created by pipeline): {e}")
            return []
        logger.error(f"Failed to fetch target schemas: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/target/tables")
def get_target_tables(schema: str):
    try:
        return backend.get_target_metadata(schema_name=schema, action="tables")
    except Exception as e:
        logger.error(f"Failed to fetch target tables: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/target/columns")
def get_target_columns(schema: str, table: str):
    try:
        return backend.get_target_metadata(schema_name=schema, table_name=table, action="columns")
    except Exception as e:
        logger.error(f"Failed to fetch target columns: {e}")
        raise HTTPException(status_code=500, detail=str(e))

class MappingRequest(BaseModel):
    src_db: str
    src_schema: str
    src_table: str
    tgt_db: str
    tgt_schema: str
    tgt_table: str
    column_map: Dict[str, Any]
    source_columns: List[str]
    target_columns: List[str]
    incremental_src_col: str = ""
    primary_keys: List[str] = []

@app.post("/mapping")
def save_mapping(mapping: MappingRequest):
    return save_mapping_batch([mapping])

@app.post("/mapping/batch")
def save_mapping_batch(mappings: List[MappingRequest]):
    logger.info(f"Received batch mapping save request for {len(mappings)} tables")
    try:
        backend.save_mapping_to_backend(mappings)
        return {"status": "success", "count": len(mappings)}
    except Exception as e:
        logger.error(f"Failed to save mappings: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

def run_ingestion_background():
    try:
        backend.run_pipeline()
    except Exception as e:
        logger.error(f"Ingestion failed: {traceback.format_exc()}")
        try:
            from src.pipeline_state_manager import get_pipeline_snapshot, update_table_status, append_log
            snapshot = get_pipeline_snapshot()
            tables = snapshot.get("table_status", [])
            if not tables:
                update_table_status("pipeline", "failed")
            else:
                for t in tables:
                    if t.get("status") not in ["completed", "failed"]:
                        update_table_status(t["table"], "failed")
            append_log(f"Pipeline execution failed: {str(e)}")
        except Exception as state_err:
            logger.error(f"Failed to update pipeline state on error: {state_err}")

@app.post("/ingest")
def start_ingestion(background_tasks: BackgroundTasks):
    table_status = []
    try:
        if os.path.exists(CONFIG_PATH):
            with open(CONFIG_PATH, "r") as f:
                config_data = json.load(f)
            source_platform = config_data.get("source", {}).get("platform", "sapsqlserver").lower()
            metadata_path = os.path.join(BACKEND_ROOT, "metadata", f"{source_platform}_metadata.csv")
            if os.path.exists(metadata_path):
                with open(metadata_path, mode='r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        tbl_name = row.get("source_table")
                        if tbl_name:
                            schema_name = row.get("source_schema") or row.get("src_schema") or row.get("SCHEMA")
                            full_name = f"{schema_name}.{tbl_name}" if schema_name else tbl_name
                            table_status.append({
                                "table": str(full_name),
                                "status": "pending"
                            })
    except Exception as e:
        logger.error(f"Failed to pre-populate table status: {e}")

    reset_pipeline_state(table_status=table_status)
    background_tasks.add_task(run_ingestion_background)
    return {"status": "success", "message": "Ingestion started in background"}

@app.post("/ingest/stop")
def stop_ingestion():
    return {"status": "success", "message": "Stop request received"}

@app.get("/ingest/status")
def get_ingestion_status():
    snapshot = get_pipeline_snapshot()
    tables = snapshot.get("table_status", [])
    if not tables:
        return {
            "status": "IDLE",
            "source_rows": 0,
            "loaded_rows": 0,
            "message": "Waiting for tasks...",
            "progress": 0,
            "logs": snapshot.get("logs", [])
        }
    
    # Identify terminal and active statuses
    active_statuses = {"extracting", "extracted", "uploading", "uploaded", "creating_table", "loading"}
    failed_statuses = {"failed", "extraction_failed", "upload_failed", "table_creation_failed", "load_failed", "validation_failed"}
    
    # Try to find a currently active table
    current = next((t for t in tables if t["status"] in active_statuses), None)
    
    if current:
        status = current["status"].upper()
    else:
        # No active tables. Are there any pending tables?
        pending = next((t for t in tables if t["status"] == "pending"), None)
        if pending:
            # Check if any prior table failed. If so, the pipeline aborted.
            failed_table = next((t for t in tables if t["status"] in failed_statuses), None)
            if failed_table:
                status = "FAILED"
                current = failed_table
            else:
                status = "PENDING"
                current = pending
        else:
            # All tables are finished (completed/skipped or failed)
            failed_table = next((t for t in tables if t["status"] in failed_statuses), None)
            if failed_table:
                status = "FAILED"
                current = failed_table
            else:
                status = "COMPLETED"
                current = tables[-1]
                
    if status == "SUCCESS":
        status = "COMPLETED"
        
    return {
        "status": status,
        "source_rows": current.get("source_row_count", 0) or 0,
        "loaded_rows": current.get("target_row_count", 0) or 0,
        "message": f"Table: {current['table']}",
        "progress": snapshot.get("progress", 0),
        "details": tables,
        "logs": snapshot.get("logs", [])
    }

@app.get("/migration-history")
def get_migration_history():
    log_dir = os.path.join(BACKEND_ROOT, "logs")
    if not os.path.exists(log_dir):
        return []
    
    try:
        history = []
        files = [
            f for f in os.listdir(log_dir)
            if f.startswith("migration_report_") and f.endswith(".csv")
        ]
        for file in files:
            file_path = os.path.join(log_dir, file)
            try:
                with open(file_path, mode='r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        source_parts = [
                            row.get('source_system', ''),
                            row.get('source_database', ''),
                            row.get('source_schema', ''),
                            row.get('source_table', '')
                        ]
                        source_str = ".".join([p for p in source_parts if p])

                        target_parts = [
                            row.get('target_system', ''),
                            row.get('target_database', ''),
                            row.get('target_schema', ''),
                            row.get('target_table', '')
                        ]
                        target_str = ".".join([p for p in target_parts if p])

                        def safe_int(val):
                            try: return int(float(val or 0))
                            except: return 0
                        
                        def safe_float(val):
                            try: return round(float(val or 0), 2)
                            except: return 0.0

                        clean_row = {
                            "id": row.get("run_id", ""),
                            "timestamp": row.get("run_timestamp", ""),
                            "source": source_str,
                            "table": row.get("source_table", "N/A"),
                            "target": target_str,
                            "status": (row.get("status") or "UNKNOWN").upper(),
                            "rows_source": safe_int(row.get("source_row_count")),
                            "rows_target": safe_int(row.get("target_row_count")),
                            "duration": safe_float(row.get("duration_seconds")),
                            "load_type": (row.get("load_type") or "SNAPSHOT").upper(),
                            "error": row.get("error_message", "")
                        }
                        history.append(clean_row)
            except Exception as file_err:
                logger.warning(f"Error reading file {file}: {file_err}")
                continue
        
        history.sort(key=lambda x: x["timestamp"], reverse=True)
        return history[:50]
    except Exception as e:
        logger.error(f"Failed to read migration history: {e}")
        return []

import threading
import pandas as pd
from fastapi.responses import FileResponse
from src.config_parser import normalize_platform_name, save_config
from src.source_metadata_extractor import source_metadata
from src.full_load_pipeline import full_load
from src.pipeline_logger import get_log_file_path, start_new_log_file
from src.pipeline_state_manager import set_current_log_file, set_progress, append_log

METADATA_DIR = os.path.join(BACKEND_ROOT, "metadata")
CONFIG_DIR = os.path.join(BACKEND_ROOT, "config")
SUPPORTED_SOURCES = {"sapsqlserver", "sqlserver", "mysql", "postgres", "oracle", "teradata"}

class Credentials(BaseModel):
    source: str
    cloud: str
    target: str
    data: Dict[str, Dict[str, str]]

class ExtractionRequest(BaseModel):
    source: str
    cloud: str
    target: str
    metadata_filename: str

class TableSelection(BaseModel):
    source: str
    database: str
    schema_name: str
    table: str
    primary_key: str

class MetadataSelection(BaseModel):
    source: str
    selections: List[TableSelection]


def build_initial_table_status(metadata_path: str):
    metadata = pd.read_csv(metadata_path)
    statuses = []
    for _, row in metadata.iterrows():
        schema = str(row.get("SCHEMA") or row.get("source_schema") or row.get("src_schema") or "").strip()
        table = str(row.get("TABLE") or row.get("source_table") or row.get("src_table") or "").strip()
        statuses.append({
            "table": f"{schema}.{table}",
            "status": "pending"
        })
    return statuses


def get_latest_pipeline_log_path():
    log_dir = os.path.join(BACKEND_ROOT, "logs")
    if not os.path.exists(log_dir):
        return None
    files = sorted(
        [f for f in os.listdir(log_dir) if f.endswith(".log")],
        key=lambda x: os.path.getmtime(os.path.join(log_dir, x)),
        reverse=True
    )
    if not files:
        return None
    return os.path.join(log_dir, files[0])


def _safe_history_timestamp(value) -> tuple[pd.Timestamp | None, str]:
    parsed = pd.to_datetime(value, errors="coerce")
    if pd.isna(parsed):
        return None, "-"
    clean = parsed.to_pydatetime().strftime("%Y-%m-%d %H:%M:%S")
    return parsed, clean


def run_full_load_pipeline(source, cloud, target):
    try:
        active_log_file = get_log_file_path() or get_latest_pipeline_log_path()
        set_current_log_file(active_log_file)
        append_log("Pipeline started...")

        full_load(source, cloud, target)

        snapshot = get_pipeline_snapshot()
        failed_tables = [
            item for item in snapshot.get("table_status", [])
            if "failed" in str(item.get("status", "")).lower()
        ]

        if failed_tables:
            failed_table_names = [item.get("table", "Unknown") for item in failed_tables]
            failed_names_str = ", ".join(failed_table_names)
            total_tables = len(snapshot.get("table_status", []))
            success_count = total_tables - len(failed_tables)
            append_log(
                f"Pipeline completed with errors. "
                f"{success_count} Tables succeeded, {len(failed_tables)} Tables failed -> [{failed_names_str}]"
            )
        else:
            migrated_tables = [
                item.get("table", "Unknown")
                for item in snapshot.get("table_status", [])
                if str(item.get("status", "")).lower() != "failed"
            ]
            table_count = len(migrated_tables)
            append_log(
                f"Pipeline completed successfully. {table_count} table(s) migrated."
            )
            set_progress(100)
    except Exception as e:
        append_log(f"Error: {str(e)}")


@app.post("/save-credentials")
async def api_save_credentials(creds: Credentials):
    try:
        config_path = save_config(
            normalize_platform_name(creds.source),
            normalize_platform_name(creds.cloud),
            normalize_platform_name(creds.target),
            creds.data
        )
        return {"message": "Credentials saved successfully", "config_path": config_path}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/fetch-metadata")
async def api_fetch_metadata(source: str, cloud: str, target: str):
    try:
        source = normalize_platform_name(source)
        cloud = normalize_platform_name(cloud)
        target = normalize_platform_name(target)
        config_filename = f"{source}_{cloud}_{target}.cfg"
        config_path = os.path.join(CONFIG_DIR, config_filename)

        if not os.path.exists(config_path):
            raise HTTPException(
                status_code=404,
                detail="Configuration not found. Please save credentials first."
            )

        df = source_metadata(source, config_path)
        if df is not None:
            return df.to_dict(orient="records")
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Metadata retrieval failed for source {source}"
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/save-metadata")
async def api_save_metadata(metadata: MetadataSelection):
    try:
        normalized_source = normalize_platform_name(metadata.source)
        filename = f"{normalized_source}_metadata.csv"
        filepath = os.path.join(METADATA_DIR, filename)

        data = [sel.model_dump() for sel in metadata.selections]
        df = pd.DataFrame(data)

        if df.empty:
            raise HTTPException(
                status_code=400,
                detail="Please select at least one table before saving metadata."
            )

        required_columns = ["database", "schema_name", "table"]
        missing_values = df[required_columns].isna() | df[required_columns].astype(str).apply(
            lambda col: col.str.strip().isin(["", "nan", "None"])
        )

        if missing_values.any(axis=None):
            raise HTTPException(
                status_code=400,
                detail="Metadata is missing database, schema, or table. Fetch metadata again before starting migration."
            )

        df = df.rename(columns={
            "source": "SOURCE",
            "database": "DATABASE",
            "schema_name": "SCHEMA",
            "table": "TABLE",
            "primary_key": "PRIMARY_KEY"
        })

        df["SOURCE"] = df["SOURCE"].astype(str).map(
            lambda value: normalize_platform_name(value).upper()
        )

        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        df.to_csv(filepath, index=False)

        return {"message": f"Metadata saved successfully to {filename}"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/start-extraction")
async def api_start_extraction(req: ExtractionRequest, background_tasks: BackgroundTasks):
    try:
        source = normalize_platform_name(req.source)
        cloud = normalize_platform_name(req.cloud)
        target = normalize_platform_name(req.target)
        config_filename = f"{source}_{cloud}_{target}.cfg"
        config_path = os.path.join(CONFIG_DIR, config_filename)

        if not os.path.exists(config_path):
            raise HTTPException(status_code=404, detail="Configuration not found.")

        metadata_filename = f"{source}_metadata.csv"
        metadata_path = os.path.join(METADATA_DIR, metadata_filename)
        if not os.path.exists(metadata_path):
            raise HTTPException(
                status_code=404,
                detail=f"Metadata file {metadata_filename} not found"
            )

        if source not in SUPPORTED_SOURCES:
            raise HTTPException(
                status_code=400,
                detail=f"Source {source} not supported"
            )

        active_log_file = start_new_log_file()
        table_status = build_initial_table_status(metadata_path)
        reset_pipeline_state(
            log_file=active_log_file,
            table_status=table_status
        )

        background_tasks.add_task(run_full_load_pipeline, source, cloud, target)
        return {"message": "Pipeline started"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/migrations-history")
def get_migrations_history():
    log_dir = os.path.join(BACKEND_ROOT, "logs")
    if not os.path.exists(log_dir):
        return []
        
    try:
        files = [
            f for f in os.listdir(log_dir)
            if f.startswith("migration_report_") and f.endswith(".csv")
        ]
        df_list = []
        for file in files:
            file_path = os.path.join(log_dir, file)
            try:
                df_list.append(pd.read_csv(file_path))
            except Exception as e:
                logger.warning(f"Failed to read report file {file}: {e}")
                
        if not df_list:
            return []
            
        df = pd.concat(df_list, ignore_index=True)
        migrations = []
        
        if "run_timestamp" in df.columns:
            df["_history_sort_time"] = pd.to_datetime(df["run_timestamp"], errors="coerce")
        elif "start_time" in df.columns:
            df["_history_sort_time"] = pd.to_datetime(df["start_time"], errors="coerce")
        else:
            df["_history_sort_time"] = pd.NaT

        for run_id, group in df.groupby("run_id", sort=False):
            run_timestamp = group["run_timestamp"].iloc[0] if "run_timestamp" in group else None
            source = str(group["source_system"].iloc[0])
            target = str(group["target_system"].iloc[0])
            
            statuses = group["status"].astype(str).str.upper().tolist()
            if "FAILED" in statuses:
                overall_status = "Failed"
            elif all(s in ["SUCCESS", "SKIPPED"] for s in statuses):
                overall_status = "Completed"
            else:
                overall_status = "In Progress"
                
            duration = pd.to_numeric(group["duration_seconds"], errors="coerce").sum(skipna=True)
            duration_str = f"{int(duration // 60)}m {int(duration % 60)}s" if duration > 0 else "-"

            parsed_run_time, time_str = _safe_history_timestamp(run_timestamp)
            sort_time = group["_history_sort_time"].max(skipna=True)
            if pd.isna(sort_time):
                if "start_time" in group.columns:
                    sort_time = pd.to_datetime(group["start_time"], errors="coerce").max(skipna=True)
                if pd.isna(sort_time):
                    sort_time = parsed_run_time

            error_message = ""
            if "error_message" in group.columns:
                errors = (
                    group["error_message"]
                    .dropna()
                    .astype(str)
                    .map(str.strip)
                )
                error_message = "; ".join(dict.fromkeys(error for error in errors if error))

            migrations.append({
                "id": f"#MIG-{str(run_id)[:6].upper()}",
                "name": f"Migration to {target}",
                "source": source,
                "target": target,
                "status": overall_status,
                "errorMessage": error_message,
                "time": time_str,
                "duration": duration_str,
                "_sort_time": sort_time
            })

        migrations.sort(
            key=lambda x: x.get("_sort_time") if pd.notna(x.get("_sort_time")) else pd.Timestamp.min,
            reverse=True
        )
        for item in migrations:
            item.pop("_sort_time", None)
        return migrations
    except Exception as e:
        print("Error fetching history:", str(e))
        return []


@app.get("/migration-status")
def migration_status():
    snapshot = get_pipeline_snapshot()
    return {
        "progress": snapshot.get("progress", 0),
        "table_status": snapshot.get("table_status", []),
        "logs": snapshot.get("logs", []),
        "log_file": snapshot.get("current_log_file")
    }


@app.get("/download-logs")
def download_logs():
    snapshot = get_pipeline_snapshot()
    log_path = snapshot.get("current_log_file") or get_latest_pipeline_log_path()

    if not log_path or not os.path.exists(log_path):
        raise HTTPException(status_code=404, detail="Log file not found")

    return FileResponse(log_path, filename=os.path.basename(log_path))


# MDM Integration Endpoints
from mdm_helper import MDMHelper
mdm_helper = MDMHelper()

class MDMConnectionRequest(BaseModel):
    account: str
    username: str
    password: str
    warehouse: str
    database: Optional[str] = None
    schema: Optional[str] = "PUBLIC"

class MDMConfigureRequest(BaseModel):
    creds: Dict[str, Any]
    group_name: str
    source_system: str
    src_db: str
    stg_schema: str
    stg_table: str
    tgt_schema: str
    tgt_table: str
    merge_key: str
    stg_merge_key: str
    column_mapping: List[Dict[str, Any]]
    stream_name: Optional[str] = ""

class MDMRunRequest(BaseModel):
    creds: Dict[str, Any]
    group_name: str

class MDMDatabasesRequest(BaseModel):
    creds: Dict[str, Any]

class MDMSchemasRequest(BaseModel):
    creds: Dict[str, Any]
    database: str

class MDMReplicateRequest(BaseModel):
    creds: Dict[str, Any]
    group_name: str
    tables: List[Dict[str, Any]]

class MDMConfigureBatchRequest(BaseModel):
    creds: Dict[str, Any]
    group_name: str
    configs: List[Dict[str, Any]]

@app.post("/mdm/test-connection")
def mdm_test_connection(req: MDMConnectionRequest):
    try:
        conn = mdm_helper.get_connection(req.model_dump())
        conn.close()
        return {"status": "success", "message": "Connected successfully to Snowflake"}
    except Exception as e:
        logger.error(f"MDM test connection failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/mdm/databases")
def mdm_get_databases(req: MDMDatabasesRequest):
    try:
        dbs = mdm_helper.fetch_databases(req.creds)
        return dbs
    except Exception as e:
        logger.error(f"MDM fetch databases failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/mdm/schemas")
def mdm_get_schemas(req: MDMSchemasRequest):
    try:
        schemas = mdm_helper.fetch_schemas(req.creds, req.database)
        return schemas
    except Exception as e:
        logger.error(f"MDM fetch schemas failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/mdm/tables")
def mdm_get_tables(req: Dict[str, Any]):
    try:
        creds = req.get("creds", {})
        schema = req.get("schema", "PUBLIC")
        tables = mdm_helper.fetch_tables(creds, schema)
        return tables
    except Exception as e:
        logger.error(f"MDM fetch tables failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/mdm/columns")
def mdm_get_columns(req: Dict[str, Any]):
    try:
        creds = req.get("creds", {})
        schema = req.get("schema", "PUBLIC")
        table = req.get("table", "")
        cols = mdm_helper.fetch_columns(creds, schema, table)
        return cols
    except Exception as e:
        logger.error(f"MDM fetch columns failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/mdm/replicate-to-bronze")
def mdm_replicate_to_bronze(req: MDMReplicateRequest):
    try:
        res = mdm_helper.replicate_to_bronze(req.creds, req.tables)
        return {"status": "success", "results": res}
    except Exception as e:
        logger.error(f"MDM replicate to bronze failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/mdm/configure")
def mdm_configure(req: MDMConfigureRequest):
    try:
        creds = req.creds
        mdm_helper.deploy_structures(creds)
        mdm_helper.configure_mapping(creds, req.model_dump())
        mdm_helper.deploy_procedures(creds)
        return {"status": "success", "message": "MDM configuration and database structures deployed successfully"}
    except Exception as e:
        logger.error(f"MDM configuration deployment failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/mdm/configure/batch")
def mdm_configure_batch(req: MDMConfigureBatchRequest):
    try:
        mdm_helper.configure_batch(req.creds, req.group_name, req.configs)
        return {"status": "success", "message": "Batch MDM configuration deployed successfully"}
    except Exception as e:
        logger.error(f"MDM batch configuration deployment failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/mdm/run")
def mdm_run(req: MDMRunRequest):
    try:
        res = mdm_helper.run_mdm(req.creds, req.group_name)
        return {"status": "success", "results": res}
    except Exception as e:
        logger.error(f"MDM execution failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/mdm/status")
def mdm_status(req: MDMRunRequest):
    try:
        logs = mdm_helper.fetch_audit_logs(req.creds, req.group_name)
        records = mdm_helper.fetch_master_records(req.creds, req.group_name)
        return {"logs": logs, "records": records}
    except Exception as e:
        logger.error(f"MDM fetch status failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
def health():
    return {"status": "ok"}



if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
