from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import os
import pandas as pd
from typing import Dict, List
import threading

from src.parse_config import normalize_platform_name, save_config
from src.source_metadata import source_metadata
from src.Full_load import full_load
from src.custom_logger import get_log_file_path, start_new_log_file
from src.pipeline_state import (
    append_log,
    get_pipeline_snapshot,
    reset_pipeline_state,
    set_current_log_file,
    set_progress,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

import sys


app = FastAPI(title="Ingestion Pipeline API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Directories
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(BASE_DIR)

CONFIG_DIR = os.path.join(BASE_DIR, "config")
METADATA_DIR = os.path.join(BASE_DIR, "metadata")

os.makedirs(CONFIG_DIR, exist_ok=True)
os.makedirs(METADATA_DIR, exist_ok=True)

SUPPORTED_SOURCES = {"sapsqlserver", "sqlserver", "mysql", "postgres", "oracle"}


# =========================
# Models
# =========================

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


# =========================
# Helper: Background Job
# =========================

def build_initial_table_status(metadata_path: str):
    metadata = pd.read_csv(metadata_path)
    statuses = []
 
    for _, row in metadata.iterrows():
        schema = str(row["SCHEMA"]).strip()
        table = str(row["TABLE"]).strip()
        statuses.append({
            "table": f"{schema}.{table}",
            "status": "pending"
        })

    return statuses


def get_latest_pipeline_log_path():
    log_dir = os.path.join(BASE_DIR, "logs")

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


def run_pipeline(source, cloud, target):
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

            # 👉 ADD THIS (small addition)
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
            table_names = ", ".join(migrated_tables) if migrated_tables else "Unknown"
            append_log(
                f"Pipeline completed successfully. {table_count} table(s) migrated."
            )
            set_progress(100)

    except Exception as e:
        append_log(f"Error: {str(e)}")


# =========================
# APIs
# =========================

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

        df.to_csv(filepath, index=False)

        return {"message": f"Metadata saved successfully to {filename}"}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/start-extraction")
async def api_start_extraction(req: ExtractionRequest):
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

        thread = threading.Thread(
            target=run_pipeline,
            args=(source, cloud, target),
            daemon=True 
        )
        thread.start()

        return {"message": "Pipeline started"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/migrations-history")
def get_migrations_history():
    csv_path = os.path.join(BASE_DIR, "logs", "migration_log_master.csv")
    if not os.path.exists(csv_path):
        return []
        
    try:
        df = pd.read_csv(csv_path)
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
                
            # Compute total duration from rows that have an end time (skipping empty/pending ones)
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

@app.get("/health")
def health():
    return {"status": "ok"}


# =========================
# Run Server
# =========================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
