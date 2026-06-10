"""
Full Load Pipeline Orchestrator
 
This module orchestrates the end-to-end full load migration pipeline:
Source → Extract → Parquet → Cloud → Target → Validation → Logging
"""
 
# ─────────────────────────────────────────────────────────────────────────────
# Standard Library Imports
# ─────────────────────────────────────────────────────────────────────────────
import os
import pandas as pd
from datetime import datetime
 
# ─────────────────────────────────────────────────────────────────────────────
# Internal Module Imports
# ─────────────────────────────────────────────────────────────────────────────
from src.connections import get_Source_connection, get_Target_connection
from src.data_extraction import extract_source_data
from src.aws_client import upload_to_s3, move_to_archive_aws
from src.azure_client import upload_to_azure, move_to_archive_azure
from src.gcp_client import upload_to_gcp, move_to_archive_gcp
from src.Create_scripts import (
    create_databricks_objects,
    create_snowflake_objects,
    create_bigquery_objects
    )
 
from src.control_table import (
    create_control_table_snowflake,
    create_control_table_databricks,
    create_control_table_bigquery,
    insert_table_log_snowflake,
    insert_table_log_databricks,
    insert_table_log_bigquery
)
from src.data_load import (
    load_s3_to_databricks,
    load_s3_to_snowflake,
    load_azure_to_snowflake,
    load_azure_to_databricks,
    load_gcs_to_bigquery
)
from src.custom_logger import get_logger
from src.pipeline_log_report import PipelineLogger
from src.row_validation import (
    get_source_row_count,
    get_target_row_count,
    get_parquet_row_count
)
from src.pipeline_state import update_table_status, update_table_metrics
from src.pipeline_state import append_log
 
logger = get_logger()

# Determine project base directory
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def get_mapping_source_name(source: str) -> str:
    if source in {"sapsqlserver", "sqlserver"}:
        return "sqlserver"

    return source
 
# -------------------------------------------------------------------
# UTILITY FUNCTIONS
# -------------------------------------------------------------------
 
def validate_files(config_path: str, metadata_path: str) -> None:
    """
    Validate configuration and metadata files exist.
 
    Args:
        config_path (str): Path to configuration file
        metadata_path (str): Path to metadata file
 
    Raises:
        FileNotFoundError: If any required file is missing
    """
    try:
        if not os.path.exists(config_path):
            raise FileNotFoundError(f"Config file not found: {config_path}")
 
        if not os.path.exists(metadata_path):
            raise FileNotFoundError(f"Metadata file not found: {metadata_path}")
       
       
        logger.info(f"Config file verified     : {config_path}")
        logger.info(f"Metadata file verified   : {metadata_path}")
 
 
    except Exception as e:
        logger.error(f"Unexpected error during file validation: {str(e)}")
        raise
 
def upload_file_to_cloud(
    cloud: str,
    config_path: str,
    file_name: str,
    file_path: str,
    folder_structure: str,
    log: dict
):
    """
    Upload parquet file to cloud storage.
 
    Supports AWS S3 and Azure Blob Storage adn GCS.
 
    Returns:
        tuple: (cloud_path, secondary_path)
    """
    if cloud.lower() == "aws":
 
        logger.info(f"Uploading {file_name} to AWS S3")
       
        try:
            move_to_archive_aws(config_path, file_name, folder_structure)
       
            logger.info(f"Previous S3 file archived successfully")
 
        except Exception as archive_err:
            # Non-fatal — log warning but continue with upload
            logger.warning(
                f"Archive step failed for '{file_name}' (non-fatal): {str(archive_err)}"
            )
 
        try:
            s3_path = upload_to_s3(
                config_path,
                file_name,
                file_path,
                folder_structure
            )
 
            log["cloud_path"] = s3_path
           
            return s3_path
       
        except Exception as s3_err:
            logger.error(f"S3 upload failed for '{file_name}': {str(s3_err)}")
            raise
 
    elif cloud.lower() == "azure":
        try:
            move_to_archive_azure(config_path, folder_structure)
       
            logger.info(f"Previous files archived successfully")
 
        except Exception as archive_err:
            # Non-fatal — log warning but continue with upload
            logger.warning(
                f"Archive step failed for '{file_name}' (non-fatal): {str(archive_err)}"
            )
 
        logger.info(f"Uploading {file_name} to Azure Blob Storage")
 
        try:
            cloud_path = upload_to_azure(
                config_path,
                file_name,
                file_path,
                folder_structure
            )
 
            log["cloud_path"] = cloud_path
            return cloud_path
       
        except Exception as azure_err:
            logger.error(f"Azure upload failed for '{file_name}': {str(azure_err)}")
            raise
 
    elif cloud.lower() == "gcp":        
 
        try:
            move_to_archive_gcp(config_path, folder_structure)
       
            logger.info(f"Previous files archived successfully")
 
        except Exception as archive_err:
            # Non-fatal — log warning but continue with upload
            logger.warning(
                f"Archive step failed for '{file_name}' (non-fatal): {str(archive_err)}"
            )
 
        logger.info(f"Uploading {file_name} to GCS")
 
        try:
            gcs_path = upload_to_gcp(
                config_path,
                file_name,
                file_path,
                folder_structure
            )
 
            log["cloud_path"] = gcs_path
 
            return gcs_path
       
        except Exception as gcp_err:
            logger.error(f"GCP upload failed for '{file_name}': {str(gcp_err)}")
            raise
 
    else:
        logger.info(f"Unsupported cloud provider: {cloud}")
        raise Exception(f"Unsupported cloud provider: {cloud}")
 
def create_target_objects(
    target: str,
    source: str,
    source_conn,
    cloud,
    target_conn,
    config_path: str,
    mapping_path: str,
    database: str,
    schema: str,
    table: str
) -> None:
    """
    Create tables and objects in target system.
    """
    logger.info(
        f"Creating target objects on '{target}' for table: "
        f"{database}.{schema}.{table}"
    )
    try:
        if target == "databricks":
            create_databricks_objects(
                source,
                source_conn,
                cloud,
                target_conn,
                config_path,
                mapping_path,
                database,
                schema,
                table
            )
 
        elif target == "snowflake":
            create_snowflake_objects(
                source,
                source_conn,
                cloud,
                target_conn,
                config_path,
                mapping_path,
                database,
                schema,
                table
            )
        elif target == "bigquery":
       
 
            create_bigquery_objects(
                source,
                source_conn,
                target_conn,
                config_path,
                mapping_path,
                database,
                schema,
                table
            )
        else:
            error_msg = (
                f"Unsupported target system: '{target}'. "
                f"Valid options are: 'databricks', 'snowflake', 'bigquery'."
            )
            logger.error(error_msg)
            raise ValueError(error_msg)
 
        logger.info(
            f"Target objects created successfully on '{target}' "
        )
 
   
    except Exception as e:
        logger.error(
            f"Failed to create target objects on '{target}' for "
            f"{database}.{schema}.{table}: {str(e)}"
        )
        raise
 
def create_control_table_on_target(target, target_conn, database):
 
    """
    Create control table in target system.
    """
 
    try:
        if target == "snowflake":
            create_control_table_snowflake(target_conn, database)
            logger.info("Snowflake control table created successfully.")
 
        elif target == "databricks":
            create_control_table_databricks(target_conn, database)
            logger.info("Databricks control table created successfully.")
        elif target == "bigquery":
            create_control_table_bigquery(target_conn, database)
 
        else:
            logger.info(
                f"Control table creation not required for target '{target}'. "
                f"Skipping."
            )
 
    except Exception as e:
        logger.error(
            f"Failed to create control table on '{target}' "
            f"(database: {database}): {str(e)}"
        )
 
def load_into_target(
    target_conn,
    target: str,
    cloud: str,
    config_path: str,
    database: str,
    schema: str,
    table: str,
    folder_structure: str,
    primary_keys
) -> None:
    """
    Load parquet data into target system.
    """
    try:
        # ── Databricks Loaders ───────────────────────────────────────────────
        if target == 'databricks':
 
            if cloud.lower() == 'aws':
                # s3_folder = os.path.dirname(cloud_path) + "/"
                load_s3_to_databricks(
                    target_conn,
                    config_path,
                    schema,
                    table,
                    folder_structure,
                    primary_keys
                )
 
            elif cloud.lower() == 'azure':
                load_azure_to_databricks(
                    target_conn,
                    config_path,
                    schema,
                    table,
                    folder_structure,
                    primary_keys
                )
       
        # ── Snowflake Loaders ────────────────────────────────────────────────
        elif target == 'snowflake':
            if cloud.lower() == 'aws':
                load_s3_to_snowflake(
                    target_conn,
                    config_path,
                    schema,
                    table,
                    folder_structure,
                    primary_keys
                )
            elif cloud.lower() == 'azure':
                load_azure_to_snowflake(
                    target_conn,
                    config_path,
                    schema,
                    table,
                    folder_structure,
                    primary_keys
                )
 
        # ── BigQuery Loader ──────────────────────────────────────────────────
        elif target == "bigquery":
            load_gcs_to_bigquery(
                target_conn,
                config_path,
                database,
                schema,
                table,
                folder_structure,
                primary_keys
            )
 
            logger.info(
                f"Data load completed successfully into '{target}' | "
                f"table: {schema}.{table}"
            )
 
    except Exception as e:
        logger.error(
            f"Data load failed into '{target}' (cloud: {cloud}) for "
            f"{schema}.{table}: {str(e)}"
        )
        raise
 
def delete_local_file(file_path: str, log: dict) -> None:
    """
    Deletes a local file safely after successful upload.
 
    Args:
        file_path (str): Path to the local file
        log (dict): Pipeline log dictionary (for tracking cleanup status)
    """
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
            logger.info(f"Local file Not deleted after upload: {file_path}")
            log["local_cleanup"] = "SUCCESS"
        else:
            logger.info(f"File not found for deletion: {file_path}")
            log["local_cleanup"] = "FILE_NOT_FOUND"
 
    except Exception as e:
        logger.error(f"Failed to delete local file: {str(e)}")
        log["local_cleanup"] = "FAILED"
 
def should_skip_step(last_status, step_name):
    return (
        last_status is not None and
        str(last_status.get(step_name)).upper() in ["SUCCESS", "SKIPPED"] and
        str(last_status.get("status")).upper() in ["SUCCESS", "SKIPPED"]
    )
 
 
 
# -------------------------------------------------------------------
# MAIN PIPELINE FUNCTION
# -------------------------------------------------------------------
 
def full_load(source: str, cloud: str, target: str) -> None:
    """
    Execute full data migration pipeline.
 
    Pipeline Steps:
        1. Validate config and metadata files
        2. Connect to source
        3. Read metadata tables
        4. Extract data to parquet
        5. Upload parquet to cloud
        6. Create target tables
        7. Load data into target
        8. Validate row counts
        9. Log pipeline execution
 
    Args:
        source (str): Source system (e.g., sqlserver)
        cloud (str): Cloud provider (aws / azure)
        target (str): Target system (databricks / snowflake)
    """
 
    config_path = os.path.join(
        base_dir,
        "config",
        f"{source}_{cloud}_{target}.cfg"
    )
 
    metadata_path = os.path.join(
        base_dir,
        "metadata",
        f"{source}_metadata.csv"
    )

    source_conn = None
    target_conn = None
    pipeline_logger = PipelineLogger(base_dir)
    had_failures = False

    try:
        # -------------------------------------------------------
        # STEP 5: DATA VALIDATION
        # Compare source and target row counts
        # Fail pipeline if mismatch detected
        # -------------------------------------------------------
        validate_files(config_path, metadata_path)
 
        logger.info("Starting Full Load Pipeline")
 
        # Source connection
        source_conn = get_Source_connection(config_path, source)
        # Target connection
        target_conn = get_Target_connection(config_path, target)
       
        # -------------------------------------------------------
        # LOADING METADATA FILE
        # Read metadata CSV which contains list of tables to process
        # Fail pipeline if metadata file is missing/corrupt
        # -------------------------------------------------------
 
        try:
            metadata = pd.read_csv(metadata_path)
        except Exception as e:
            logger.error(f"Failed to read metadata file: {metadata_path} | Error: {str(e)}")
            raise
       
        # -------------------------------------------------------
        # ITERATE THROUGH METADATA
        # Loop through each table configuration defined in metadata
        # -------------------------------------------------------
        for _, row in metadata.iterrows():
            # -------------------------------------------------------
            # VALIDATE REQUIRED METADATA COLUMNS
            # Ensure required fields exist in metadata row
            # Skip table if any required column is missing
            # -------------------------------------------------------
            try:
                database = row["DATABASE"]
                schema = row["SCHEMA"]
                table = row["TABLE"]
                primary_keys = [pk.strip() for pk in str(row['PRIMARY_KEY']).split(",")]
            except KeyError as e:
                logger.error(f"Missing column in metadata: {str(e)} | Row: {row}")
                continue
 
            # -------------------------------
            # DB Names
            # -------------------------------
            raw_database = f"{database}_raw"
            tgt_database = f"{database}_tgt"
            ui_table_name = f"{schema}.{table}"
 
            logger.info(f"Processing table {raw_database}.{schema}.{table}")
            update_table_status(ui_table_name, "extracting")
 
            # -------------------------------------------------------
            # INITIALIZE TABLE-LEVEL LOGGING
            # Create log structure to track execution status for this table
            # -------------------------------------------------------
            table_log = pipeline_logger.start_table_log(
                            source, cloud, target,
                            database, schema, table
                            )
           
            # -------------------------------------------------------
            # PREPARE FILE SYSTEM PATHS
            # Create safe table name and folder structure for extraction
            # -------------------------------------------------------
            try:
                safe_table = table.replace("/", "_")
                folder_structure = f"{database}/{schema}/{safe_table}"
 
                local_folder_path = os.path.join(
                    base_dir,
                    "Extract",
                    folder_structure
                )
 
                try:
                    src_count = None
                    # Source row count
                    src_count = get_source_row_count(
                        source_conn,
                        database,
                        schema,
                        table,
                        source
                    )
                    table_log["source_row_count"] = src_count
                    update_table_metrics(ui_table_name, source_row_count=src_count)
 
                except Exception as e:
                    table_log["source_row_count"] = None
                    table_log["error_message"] = str(e)
                    logger.error(f"[{table}] Failed to fetch source row count: {e}")
 
                # -------------------------------------------------------
                # LOAD PREVIOUS PIPELINE EXECUTION LOGS
                # Used for checkpointing (skip already completed steps)
                # -------------------------------------------------------
                log_file = os.path.join(base_dir, "logs", "migration_log_master.csv")
 
                last_status = None
 
                if os.path.exists(log_file):
                    try:
                        df_logs = pd.read_csv(log_file)
                    except Exception as e:
                        logger.warning(f"Failed to read log file, continuing fresh: {str(e)}")
                        df_logs = pd.DataFrame()
 
                    df_table = df_logs[
                                (df_logs["source_system"] == source) &
                                (df_logs["cloud"] == cloud) &
                                (df_logs["target_system"] == target) &
                                (df_logs["database_name"] == database) &
                                (df_logs["schema_name"] == schema) &
                                (df_logs["table_name"] == table)
                            ]
 
                    if not df_table.empty:
                        df_table = df_table.sort_values("run_timestamp")
                        last_status = df_table.iloc[-1]
 
 
                # -------------------------------------------------------
                # CHECKPOINT: SKIP STEP IF ALREADY COMPLETED
                # Uses previous pipeline run logs to determine whether
                # this step was already successfully executed
                # -------------------------------------------------------
                if src_count is not None and src_count == 0:
                    # -------------------------------------------------------
                    # EMPTY TABLE: Skip extraction and upload entirely
                    # No parquet file needed, no cloud upload needed
                    # -------------------------------------------------------
                    logger.warning(f"[{table}] Source table has 0 rows — skipping extraction and upload to cloud.")
                    table_log["extraction_status"] = "SKIPPED"
                    table_log["upload_status"] = "SKIPPED"
                    table_log["parquet_row_count"] = 0
                    table_log["local_cleanup"] = "SKIPPED"
                    update_table_status(ui_table_name, "extracted")
                    update_table_status(ui_table_name, "uploaded")
               
                else:
                    if should_skip_step(last_status, "extraction_status"):
                        candidate_file_path = last_status["parquet_file_path"]

                        if isinstance(candidate_file_path, str) and candidate_file_path.strip() and os.path.exists(candidate_file_path):
                            logger.info("Skipping extraction (already done)")
                            file_path = candidate_file_path
                            table_log["extraction_status"] = "SKIPPED"
                        else:
                            logger.info("Previous parquet file is unavailable locally. Re-running extraction.")
                            file_path = extract_source_data(
                                source_conn,
                                source,
                                local_folder_path,
                                database,
                                schema,
                                table,
                                target
                            )

                            table_log["extraction_status"] = "SUCCESS"
                            update_table_status(ui_table_name, "extracted")

                            parquet_count = get_parquet_row_count(file_path)
                            table_log["parquet_row_count"] = parquet_count
                            table_log["parquet_file_path"] = file_path
                        
                    else:
                        try:
                            # -------------------------------------------------------
                            # STEP 1: DATA EXTRACTION
                            # Extract data from source system into parquet format
                            # If already extracted in previous successful run, skip
                            # -------------------------------------------------------
 
                            file_path = extract_source_data(
                                source_conn,
                                source,
                                local_folder_path,
                                database,
                                schema,
                                table,
                                target
                            )
 
                            table_log["extraction_status"] = "SUCCESS"
                            update_table_status(ui_table_name, "extracted")
 
                            parquet_count = get_parquet_row_count(file_path)
 
                            table_log["parquet_row_count"] = parquet_count
                            table_log["parquet_file_path"] = file_path
 
                           
 
                        except Exception as e:
                            table_log["extraction_status"] = "FAILED"
                            table_log["error_message"] = str(e)
                            raise
 
                    # Parquet Full File path with file name
                    file_name = os.path.basename(file_path)
 
                    try:
                        update_table_status(ui_table_name, "uploading")
                        # -------------------------------------------------------
                        # CHECKPOINT: SKIP STEP IF ALREADY COMPLETED
                        # Uses previous pipeline run logs to determine whether
                        # this step was already successfully executed
                        # -------------------------------------------------------
                        if should_skip_step(last_status, "upload_status"):
                            candidate_cloud_path = last_status["cloud_path"]
                            if isinstance(candidate_cloud_path, str) and candidate_cloud_path.strip():
                                logger.info("Skipping upload (already done)")
                                cloud_path = candidate_cloud_path
                                table_log["upload_status"] = "SKIPPED"
                                update_table_status(ui_table_name, "uploaded")
                            else:
                                logger.info("Previous cloud path is unavailable. Re-uploading parquet.")
                                cloud_path = upload_file_to_cloud(
                                    cloud,
                                    config_path,
                                    file_name,
                                    file_path,
                                    folder_structure,
                                    table_log
                                )

                                table_log["upload_status"] = "SUCCESS"
                                update_table_status(ui_table_name, "uploaded")
                            
                        else:
 
                            # -------------------------------------------------------
                            # STEP 2: UPLOAD TO CLOUD STORAGE
                            # Upload extracted parquet file to cloud (Azure/AWS)
                            # Also deletes local file after successful upload
                            # If already Uploaded in previous successful run, skips Upload
                            # -------------------------------------------------------
 
                            cloud_path = upload_file_to_cloud(
                                cloud,
                                config_path,
                                file_name,
                                file_path,
                                folder_structure,
                                table_log
                            )
 
                            table_log["upload_status"] = "SUCCESS"
                            update_table_status(ui_table_name, "uploaded")
                           
                            try:
                                # Cleaning local files
                                delete_local_file(file_path, table_log)
 
                            except Exception as e:
                                logger.warning(f"Failed to delete local file: {str(e)}")
                                table_log["local_cleanup"] = "FAILED"
                           
 
                    except Exception as upload_err:
                        table_log["upload_status"] = "FAILED"
                        table_log["error_message"] = str(upload_err)
                        update_table_status(ui_table_name, "upload_failed")
 
                        logger.error(f"Upload failed for {file_name}: {str(upload_err)}")
 
                        table_log["local_cleanup"] = "SKIPPED"
                       
 
                        raise
                   
                # -------------------------------------------------------
                # CHECKPOINT: SKIP STEP IF ALREADY COMPLETED
                # Uses previous pipeline run logs to determine whether
                # this step was already successfully executed
                # -------------------------------------------------------
               
                if (
                    should_skip_step(last_status, "table_creation_status") and
                    table_log.get("upload_status") in ["SUCCESS", "SKIPPED"]
                    ):
                    logger.info("Skipping table creation")
                    table_log["table_creation_status"] = "SKIPPED"
                   
                else:                
                    update_table_status(ui_table_name, "creating_table")
                    # -------------------------------------------------------
                    # LOAD DATA TYPE MAPPING CONFIGURATION
                    # Used for converting source schema to target schema
                    # -------------------------------------------------------
                    mapping_path = os.path.join(
                        base_dir,
                        "Data_type_Mapping",
                        f"{get_mapping_source_name(source)}_{target}.csv"
                    )
                    try:
                        # -------------------------------------------------------
                        # STEP 3: TARGET TABLE CREATION
                        # Create RAW and TARGET tables using mapping config
                        # Also ensures control table exists
                        # -------------------------------------------------------
                        create_target_objects(
                            target,
                            source,
                            source_conn,
                            cloud,
                            target_conn,
                            config_path,
                            mapping_path,
                            database,
                            schema,
                            table
                        )
 
                        table_log["table_creation_status"] = "SUCCESS"
 
                        try:
 
                            create_control_table_on_target(target, target_conn, database)
 
                        except Exception as e:
                            logger.error(f"Control table creation failed: {str(e)}")
                            table_log["control_table_status"] = "FAILED"
                            raise
                       
                    except Exception as e:
                        table_log["table_creation_status"] = "FAILED"
                        table_log["error_message"] = str(e)
                        update_table_status(ui_table_name, "table_creation_failed")
                        raise
               
 
                # -------------------------------------------------------
                # CHECKPOINT: SKIP STEP IF ALREADY COMPLETED
                # Uses previous pipeline run logs to determine whether
                # this step was already successfully executed
                # -------------------------------------------------------
                if (
                    should_skip_step(last_status, "load_status") and
                    table_log.get("upload_status") in ["SUCCESS", "SKIPPED"] and
                    table_log.get("table_creation_status") in ["SUCCESS", "SKIPPED"]
                    ):
 
                    logger.info("Skipping load")
                    table_log["load_status"] = "SKIPPED"
                    update_table_status(ui_table_name, "completed")
                   
                else:
                    try:
                        update_table_status(ui_table_name, "loading")
 
                        if src_count is not None and src_count == 0:
                            logger.warning(f"[{table}] Source table has 0 rows — skipping load into target.")
                            table_log["load_status"] = "SKIPPED"
                            update_table_status(ui_table_name, "completed")
 
                        else:
                            # -------------------------------------------------------
                            # STEP 4: LOAD INTO TARGET
                            # Load data from cloud storage into target system
                            # Supports merge/insert logic based on primary keys
                            # -------------------------------------------------------
 
                            load_into_target(
                                target_conn,
                                target,
                                cloud,
                                config_path,
                                database,
                                schema,
                                table,
                                folder_structure,
                                primary_keys
                            )
 
                            table_log["load_status"] = "SUCCESS"
                            update_table_status(ui_table_name, "completed")
                       
                    except Exception as e:
                        table_log["load_status"] = "FAILED"
                        table_log["error_message"] = str(e)
                        update_table_status(ui_table_name, "load_failed")
                       
                        raise
               
                try:
                    tgt_count = None
                    # Target row count
                    tgt_count = get_target_row_count(
                        target_conn,
                        database,
                        schema,
                        table,
                        target
                    )
 
                    table_log["target_row_count"] = tgt_count
                    update_table_metrics(ui_table_name, target_row_count=tgt_count)

                except Exception as e:
                    table_log["target_row_count"] = None
                    table_log["error_message"] = str(e)
                    logger.error(f"[{table}] Failed to fetch target row count: {e}")
 
               
               
                # -------------------------------------------------------
                # VALIDATE DATA CONSISTENCY
                # Compare source and target row counts to ensure data integrity
                # Fail pipeline if mismatch detected
                # -------------------------------------------------------
                if src_count is not None and tgt_count is not None and src_count != tgt_count:
                    error_msg = f"Row count mismatch: Source={src_count}, Target={tgt_count}"
                    logger.error(error_msg)
 
                    table_log["status"] = "FAILED"
                    table_log["error_message"] = error_msg
                    update_table_status(ui_table_name, "validation_failed")
 
                    raise Exception(error_msg)
 
                table_log["status"] = "SUCCESS"
 
                logger.info(f"Completed table {table}")
 
            except Exception as e:
                had_failures = True
                table_log["status"] = "FAILED"
                table_log["error_message"] = str(e)
                if table_log.get("load_status") == "FAILED":
                    update_table_status(ui_table_name, "load_failed")
                elif table_log.get("table_creation_status") == "FAILED":
                    update_table_status(ui_table_name, "table_creation_failed")
                elif table_log.get("upload_status") == "FAILED":
                    update_table_status(ui_table_name, "upload_failed")
                elif table_log.get("extraction_status") == "FAILED":
                    update_table_status(ui_table_name, "extraction_failed")
                elif table_log.get("status") == "FAILED" and "Row count mismatch" in str(e):
                    update_table_status(ui_table_name, "validation_failed")
                else:
                    update_table_status(ui_table_name, "failed")
                append_log(f"{ui_table_name}: {str(e)}")
 
                logger.error(f"Creating table Failed for {table}: {str(e)}")
           
            # -------------------------------------------------------
            # STEP 6: LOGGING
            # Finalize and persist table-level execution logs
            # This runs regardless of SUCCESS or FAILURE
            # -------------------------------------------------------
            finally:
                # Finalize log entry for the table
                if table_log:
                    try:
                        pipeline_logger.finalize_table_log(table_log)
                        update_table_metrics(
                            ui_table_name,
                            duration_seconds=table_log.get("duration_seconds")
                        )
                        if target == "snowflake":
                            insert_table_log_snowflake(target_conn, database, table_log)
 
                        elif target == "databricks":
                            insert_table_log_databricks(target_conn, database, table_log)
                        elif target == "bigquery":
                            insert_table_log_bigquery(target_conn, database, table_log)
                    except Exception as log_err:
                        logger.error(f"CRITICAL: Logging failed but pipeline continues: {str(log_err)}")
 
           
        try:
            pipeline_logger.save_logs()
        except Exception as e:
            logger.error(f"Failed to save pipeline logs: {str(e)}")

        if had_failures:
            logger.warning("Full Load Pipeline Completed With Errors")
        else:
            logger.info("Full Load Pipeline Completed Successfully")

    except Exception as e:
        logger.error(f"Pipeline failed: {str(e)}")
        raise
 
    finally:
        if source_conn:
            source_conn.close()
            logger.info("Source Connection closed successfully")
        else:
            logger.info("Source Connection was not established")
       
        if target_conn:
            target_conn.close()
            logger.info("Target Connection closed successfully")
        else:
            logger.info("Target connection was not established")
       
   
 
 
