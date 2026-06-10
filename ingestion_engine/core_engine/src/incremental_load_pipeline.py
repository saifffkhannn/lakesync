"""
Incremental Load Pipeline Orchestrator

Source -> Parquet -> Cloud storage -> RAW -> TARGET merge.
The local CSV log is append-only history only; it is not used for restart skips.
"""

import os
from datetime import datetime, timedelta
import pandas as pd

from src.aws_s3_client import move_to_archive_aws, upload_to_s3
from src.azure_blob_client import move_to_archive_azure, upload_to_azure
from src.pipeline_control_table import (
    create_control_table_bigquery,
    create_control_table_databricks,
    create_control_table_snowflake,
    get_last_successful_run,
    insert_table_log_bigquery,
    insert_table_log_databricks,
    insert_table_log_snowflake,
)
from src.db_connections import get_Source_connection, get_Target_connection
from src.config_parser import parse_config
from src.ddl_generator import create_incremental_raw_objects
from src.pipeline_logger import get_logger
from src.data_extractor import (
    extract_sapsqlserver_incremental_data,
    extract_mysql_incremental_data,
    extract_oracle_incremental_data,
    extract_teradata_incremental_data,
)
from src.data_loader import (
    load_azure_to_databricks,
    load_azure_to_snowflake,
    load_gcs_to_bigquery,
    load_s3_to_databricks,
    load_s3_to_snowflake,
)
from src.gcp_storage_client import move_to_archive_gcp, upload_to_gcp
from src.metadata_parser import (
    normalize_metadata_row,
    target_primary_key_columns,
)
from src.pipeline_logger_report import PipelineLogger
from src.pipeline_state_manager import append_log, update_table_metrics, update_table_status
from src.data_validator import (
    get_incremental_source_row_count,
    get_parquet_row_count,
    get_target_row_count,
)

logger = get_logger()
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def validate_files(config_path, metadata_path):
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Config file not found: {config_path}")
    if not os.path.exists(metadata_path):
        raise FileNotFoundError(f"Metadata file not found: {metadata_path}")
    logger.info(f"Config file verified     : {config_path}")
    logger.info(f"Metadata file verified   : {metadata_path}")


def upload_file_to_cloud(cloud, config_path, file_name, file_path, folder_structure, log):
    cloud_name = cloud.lower()

    if cloud_name == "aws":
        try:
            move_to_archive_aws(config_path, file_name, folder_structure)
            logger.info("Previous S3 files archived successfully")
        except Exception as archive_err:
            logger.warning(f"AWS archive step failed, continuing: {str(archive_err)}")

        cloud_path = upload_to_s3(config_path, file_name, file_path, folder_structure)
        log["cloud_path"] = cloud_path
        return cloud_path

    if cloud_name == "azure":
        try:
            move_to_archive_azure(config_path, folder_structure)
            logger.info("Previous Azure files archived successfully")
        except Exception as archive_err:
            logger.warning(f"Azure archive step failed, continuing: {str(archive_err)}")

        cloud_path = upload_to_azure(config_path, file_name, file_path, folder_structure)
        log["cloud_path"] = cloud_path
        return cloud_path

    if cloud_name == "gcp":
        try:
            move_to_archive_gcp(config_path, folder_structure)
            logger.info("Previous GCS files archived successfully")
        except Exception as archive_err:
            logger.warning(f"GCS archive step failed, continuing: {str(archive_err)}")

        cloud_path = upload_to_gcp(config_path, file_name, file_path, folder_structure)
        log["cloud_path"] = cloud_path
        return cloud_path

    raise ValueError(f"Unsupported cloud provider: {cloud}")


def create_control_table_on_target(target, target_conn, database, control_schema="control_schema"):
    if target == "snowflake":
        create_control_table_snowflake(target_conn, database, control_schema)
        return
    if target == "databricks":
        create_control_table_databricks(target_conn, database, control_schema)
        return
    if target == "bigquery":
        create_control_table_bigquery(target_conn, database)
        return
    raise ValueError(f"Unsupported target for control table: {target}")


def load_into_target(
    target_conn,
    target,
    cloud,
    config_path,
    database,
    schema,
    table,
    folder_structure,
    primary_keys,
):
    if target == "databricks":
        if cloud.lower() == "aws":
            return load_s3_to_databricks(
                target_conn, config_path, schema, table, folder_structure, primary_keys
            )
        if cloud.lower() == "azure":
            return load_azure_to_databricks(
                target_conn, config_path, schema, table, folder_structure, primary_keys
            )

    if target == "snowflake":
        if cloud.lower() == "aws":
            return load_s3_to_snowflake(
                target_conn, config_path, schema, table, folder_structure, primary_keys, database
            )
        if cloud.lower() == "azure":
            return load_azure_to_snowflake(
                target_conn, config_path, schema, table, folder_structure, primary_keys, database
            )

    if target == "bigquery":
        return load_gcs_to_bigquery(
            target_conn, config_path, database, schema, table, folder_structure, primary_keys
        )

    raise ValueError(f"Unsupported load path: cloud={cloud}, target={target}")


def delete_local_file(file_path, log):
    if os.path.exists(file_path):
        os.remove(file_path)
        log["local_cleanup"] = "SUCCESS"
        logger.info(f"Local file deleted after upload: {file_path}")
    else:
        log["local_cleanup"] = "FILE_NOT_FOUND"


def control_window_start(last_run_timestamp, overlap_minutes=30):
    if last_run_timestamp is None or pd.isna(last_run_timestamp):
        return None

    if isinstance(last_run_timestamp, str):
        parsed = pd.to_datetime(last_run_timestamp)
    else:
        parsed = pd.Timestamp(last_run_timestamp)

    if parsed.tzinfo is not None:
        parsed = parsed.tz_convert(None)

    return (parsed.to_pydatetime() - timedelta(minutes=overlap_minutes)).replace(tzinfo=None)


# -----------------------------------------------------------------------------
# MODULAR STEP FUNCTIONS FOR PIPELINE
# -----------------------------------------------------------------------------

def retrieve_watermark_and_count(target_conn, target, table_metadata, load_type, control_schema, source_conn, ui_table_name, table_log):
    """
    Step 1: Retrieve watermark timestamp from target control table and calculate window.
    Fetch total pending source records in this range.
    """
    tgt_database = table_metadata.target_database
    tgt_schema = table_metadata.target_schema
    tgt_table = table_metadata.safe_target_table

    if load_type == "FULL":
        window_start = None
        last_run = None
        logger.info(f"[{ui_table_name}] FULL Load strategy active (no watermark filtering)")
    else:
        last_run = get_last_successful_run(target_conn, target, tgt_database, tgt_schema, tgt_table, control_schema)
        window_start = control_window_start(last_run, overlap_minutes=30)
        logger.info(
            f"[{ui_table_name}] Target last run timestamp = {last_run}; "
            f"Extraction window start = {window_start}"
        )

    source_count = get_incremental_source_row_count(source_conn, table_metadata, window_start)
    table_log["source_row_count"] = source_count
    update_table_metrics(ui_table_name, source_row_count=source_count)

    return window_start, last_run, source_count


def extract_delta_data(source, source_conn, local_folder_path, table_metadata, window_start, target, ui_table_name, table_log):
    """
    Step 2: Extract delta data from source based on watermark column and type mapping to Parquet.
    """
    update_table_status(ui_table_name, "extracting")
    if source == "sapsqlserver":
        file_path, batch_watermark = extract_sapsqlserver_incremental_data(
            source_conn, local_folder_path, table_metadata, window_start, target
        )
    elif source == "mysql":
        file_path, batch_watermark = extract_mysql_incremental_data(
            source_conn, local_folder_path, table_metadata, window_start, target
        )
    elif source == "oracle":
        file_path, batch_watermark = extract_oracle_incremental_data(
            source_conn, local_folder_path, table_metadata, window_start, target
        )
    elif source == "teradata":
        file_path, batch_watermark = extract_teradata_incremental_data(
            source_conn, local_folder_path, table_metadata, window_start, target
        )
    else:
        raise ValueError(f"Unsupported source for extraction: {source}")

    table_log["watermark_value"] = batch_watermark
    table_log["extraction_status"] = "SUCCESS"
    table_log["parquet_file_path"] = file_path
    table_log["parquet_row_count"] = get_parquet_row_count(file_path)
    update_table_status(ui_table_name, "extracted")
    return file_path, batch_watermark


def upload_and_stage_table_data(cloud, config_path, file_path, folder_structure, target, target_conn, tgt_database, tgt_schema, tgt_table, ui_table_name, table_log):
    """
    Step 3: Upload parquet file to cloud storage, cleanup local files, and create staging schema + staging tables.
    """
    update_table_status(ui_table_name, "uploading")
    cloud_path = upload_file_to_cloud(
        cloud,
        config_path,
        os.path.basename(file_path),
        file_path,
        folder_structure,
        table_log,
    )
    table_log["upload_status"] = "SUCCESS"
    table_log["cloud_path"] = cloud_path
    update_table_status(ui_table_name, "uploaded")
    delete_local_file(file_path, table_log)

    update_table_status(ui_table_name, "creating_table")
    # Note: Incremental load ONLY creates RAW/staging tables (does not overwrite/create Target business tables)
    create_incremental_raw_objects(target, cloud, target_conn, config_path, tgt_database, tgt_schema, tgt_table)
    table_log["table_creation_status"] = "SUCCESS"


def load_and_merge_table_data(target_conn, target, cloud, config_path, table_metadata, folder_structure, ui_table_name, table_log):
    """
    Step 4: Load cloud staged data into RAW and perform final merge with the business Target table.
    """
    tgt_database = table_metadata.target_database
    tgt_schema = table_metadata.target_schema
    tgt_table = table_metadata.safe_target_table

    update_table_status(ui_table_name, "loading")
    load_success, metrics = load_into_target(
        target_conn,
        target,
        cloud,
        config_path,
        tgt_database,
        tgt_schema,
        tgt_table,
        folder_structure,
        target_primary_key_columns(table_metadata),
    )

    if load_success:
        table_log["load_status"] = "SUCCESS"
        table_log["inserted_rows"] = metrics.get("inserted", 0)
        table_log["updated_rows"] = metrics.get("updated", 0)
        table_log["status"] = "SUCCESS"
        table_log["target_row_count"] = table_log["inserted_rows"] + table_log["updated_rows"]
    else:
        table_log["load_status"] = "FAILED"
        table_log["status"] = "FAILED"
        raise Exception("Merge operation failed on target")

    target_count = get_target_row_count(target_conn, tgt_database, tgt_schema, tgt_table, target)
    table_log["target_row_count"] = target_count
    update_table_metrics(
        ui_table_name,
        target_row_count=target_count,
        inserted_rows=table_log.get("inserted_rows", 0),
        updated_rows=table_log.get("updated_rows", 0)
    )
    update_table_status(ui_table_name, "completed")


def log_run_status(target_conn, target, tgt_database, table_log, control_schema):
    """
    Step 5: Write metadata logs to target system control/pipeline table.
    """
    if target_conn is not None:
        if target == "snowflake":
            create_control_table_snowflake(target_conn, tgt_database, control_schema)
            insert_table_log_snowflake(target_conn, tgt_database, table_log, control_schema)
        elif target == "databricks":
            insert_table_log_databricks(target_conn, tgt_database, table_log, control_schema)
        elif target == "bigquery":
            insert_table_log_bigquery(target_conn, tgt_database, table_log)


def incremental_load(source, cloud, target):
    """
    Modular Incremental Load Pipeline Orchestrator.
    Handles extraction, staging creation, file loading, and target schema merges.
    """
    from src.pipeline_logger import start_new_log_file
    from src.pipeline_state_manager import set_current_log_file
    active_log_file = start_new_log_file()
    set_current_log_file(active_log_file)

    pipeline_logger = PipelineLogger(base_dir)
    config_path = os.path.join(base_dir, "config", f"{source}_{cloud}_{target}.cfg")
    metadata_path = os.path.join(base_dir, "metadata", f"{source}_metadata.csv")

    source_conn = None
    target_conn = None
    try:
        validate_files(config_path, metadata_path)
        logger.info("Starting Modular Incremental/Full Load Pipeline")
        control_schema = "control_schema"
        load_type = "INCREMENTAL"

        try:
            cfg = parse_config(config_path)
            if "pipeline" in cfg and "load_type" in cfg["pipeline"]:
                load_type = cfg["pipeline"]["load_type"].upper()
        except Exception as config_err:
            logger.warning(f"Could not load config: {config_err}")

        source_conn = get_Source_connection(config_path, source)
        target_conn = get_Target_connection(config_path, target)
        metadata = pd.read_csv(metadata_path)

        for _, row in metadata.iterrows():
            table_log = None
            table_metadata = None

            try:
                table_metadata = normalize_metadata_row(row, source, target)
                src_database = table_metadata.source_database
                src_schema = table_metadata.source_schema
                src_table = table_metadata.source_table

                tgt_database = table_metadata.target_database
                tgt_schema = table_metadata.target_schema
                tgt_table = table_metadata.safe_target_table
                ui_table_name = table_metadata.source_table_name

                folder_structure = "/".join(filter(None, [src_database, src_schema, src_table]))
                local_folder_path = os.path.join(base_dir, "Extract", folder_structure)

                table_log = pipeline_logger.start_table_log(
                    source, cloud, target,
                    src_database, src_schema, src_table,
                    tgt_database, tgt_schema.lower(), tgt_table.lower()
                )
                table_log["load_type"] = load_type

                create_control_table_on_target(target, target_conn, tgt_database, control_schema)

                # 1. Retrieve watermark values and count source changes
                window_start, last_run, source_count = retrieve_watermark_and_count(
                    target_conn, target, table_metadata, load_type, control_schema, source_conn, ui_table_name, table_log
                )

                if source_count == 0:
                    logger.info(f"[{ui_table_name}] No rows in control window.")
                    table_log["extraction_status"] = "SUCCESS"
                    table_log["upload_status"] = "SUCCESS"
                    table_log["table_creation_status"] = "SUCCESS"
                    table_log["load_status"] = "SUCCESS"
                    table_log["parquet_row_count"] = 0
                    table_log["watermark_value"] = last_run
                    table_log["status"] = "SUCCESS"
                    try:
                        target_count = get_target_row_count(target_conn, tgt_database, tgt_schema, tgt_table, target)
                    except:
                        target_count = 0
                    update_table_metrics(
                        ui_table_name,
                        source_row_count=0,
                        target_row_count=target_count,
                        inserted_rows=0,
                        updated_rows=0
                    )
                    update_table_status(ui_table_name, "completed")
                    continue

                # 2. Extract delta data to local parquet file
                file_path, batch_watermark = extract_delta_data(
                    source, source_conn, local_folder_path, table_metadata, window_start, target, ui_table_name, table_log
                )

                # 3. Upload file to cloud storage & Create RAW/staging tables on target database
                upload_and_stage_table_data(
                    cloud, config_path, file_path, folder_structure, target, target_conn, tgt_database, tgt_schema, tgt_table, ui_table_name, table_log
                )

                # 4. Load cloud staged data into RAW and perform final merge with business Target table
                load_and_merge_table_data(
                    target_conn, target, cloud, config_path, table_metadata, folder_structure, ui_table_name, table_log
                )

            except Exception as e:
                table_name = table_metadata.source_table_name if table_metadata else "metadata-row"
                if table_log is not None:
                    table_log["status"] = "FAILED"
                    table_log["error_message"] = str(e)
                update_table_status(table_name, "failed")
                append_log(f"{table_name}: {str(e)}")
                logger.error(f"Load failed for {table_name}: {str(e)}")

            finally:
                if table_log is not None:
                    pipeline_logger.finalize_table_log(table_log)
                    table_name = table_metadata.source_table_name if table_metadata else "metadata-row"
                    update_table_metrics(table_name, duration_seconds=table_log.get("duration_seconds"))

                    try:
                        log_run_status(target_conn, target, tgt_database, table_log, control_schema)
                    except Exception as db_log_err:
                        logger.error(f"Failed to log run status to target database: {db_log_err}")

        logger.info("Pipeline Execution Completed Successfully")

    finally:
        try:
            pipeline_logger.save_logs()
        except Exception as save_err:
            logger.error(f"Failed to save pipeline logs: {save_err}")
        if source_conn:
            source_conn.close()
            logger.info("Source Connection closed")
        if target_conn:
            target_conn.close()
            logger.info("Target Connection closed")
