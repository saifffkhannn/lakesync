from src.pipeline_logger import get_logger
from datetime import datetime
from google.cloud import bigquery
import json
import os

logger = get_logger()

def get_target_db(database):
    """
    Always returns the exact database name as provided.
    No suffix is appended for either Full Load or Incremental Load.
    """
    return database

def get_raw_db(database):
    """
    Returns the staging database name with '_stg' suffix (lowercase).
    e.g. 'bikestores' -> 'bikestores_stg'
    """
    if database.lower().endswith('_stg'):
        return database.lower()
    return f"{database.lower()}_stg"



# ---------------------------------------------------
# SAFE SQL VALUE
# ---------------------------------------------------
# Converts Python values into SQL-safe literals.
# Handles:
# - None → NULL
# - datetime → formatted string
# - str → escaped string (prevents SQL break)
# - numbers → returned as-is
# ---------------------------------------------------
def safe_sql_value(value):
    try:
        if value is None:
            return "NULL"

        if isinstance(value, datetime):
            return f"'{value.strftime('%Y-%m-%d %H:%M:%S.%f')}'"

        if isinstance(value, str):
            value = value.replace("'", "''")  # Escape single quotes
            return f"'{value}'"

        return value

    except Exception as e:
        logger.info(f"Error converting value to SQL-safe format: {str(e)}")
        raise Exception(f"safe_sql_value failed: {str(e)}")


# ===================================================
# SNOWFLAKE FUNCTIONS
# ===================================================

def create_control_table_snowflake(conn, database, control_schema="control_schema"):
    """
    Creates pipeline_control table in Snowflake target database.
    """

    cursor = conn.cursor()
    Tgt_database = get_target_db(database)

    try:
        cursor.execute(f"CREATE SCHEMA IF NOT EXISTS {Tgt_database}.{control_schema}")
        query = f"""
        CREATE TABLE IF NOT EXISTS {Tgt_database}.{control_schema}.pipeline_control (
            run_id STRING,
            run_timestamp TIMESTAMP,
            source_system STRING,
            cloud STRING,
            target_system STRING,
            source_database STRING,
            source_schema STRING,
            source_table STRING,
            target_database STRING,
            target_schema STRING,
            target_table STRING,
            source_row_count INTEGER,
            target_row_count INTEGER,
            inserted_rows INTEGER,
            updated_rows INTEGER,
            load_type STRING,
            cloud_path STRING,
            start_time TIMESTAMP,
            end_time TIMESTAMP,
            duration_seconds FLOAT,
            status STRING,
            error_message STRING,
            watermark_value TIMESTAMP
        )
        """

        cursor.execute(query)
        logger.info(f"Snowflake control table ready in {Tgt_database}.{control_schema}")

    except Exception as e:
        logger.info(f"Error creating Snowflake control table: {str(e)}")
        raise Exception(f"Snowflake table creation failed: {str(e)}")

    finally:
        try:
            cursor.close()
        except Exception:
            pass


def insert_table_log_snowflake(conn, database, log, control_schema="control_schema"):
    """
    Inserts a log record into Snowflake control table.
    """

    cursor = conn.cursor()
    Tgt_database = get_target_db(database)

    try:
        query = f"""
        INSERT INTO {Tgt_database}.{control_schema}.pipeline_control (
            run_id, run_timestamp, source_system, cloud, target_system,
            source_database, source_schema, source_table,
            target_database, target_schema, target_table,
            source_row_count, target_row_count, inserted_rows, updated_rows, load_type, cloud_path,
            start_time, end_time, duration_seconds,
            status, error_message, watermark_value
        )
        VALUES (
            {safe_sql_value(log.get("run_id"))},
            {safe_sql_value(log.get("run_timestamp"))},
            {safe_sql_value(log.get("source_system"))},
            {safe_sql_value(log.get("cloud"))},
            {safe_sql_value(log.get("target_system"))},
            {safe_sql_value(log.get("source_database"))},
            {safe_sql_value(log.get("source_schema"))},
            {safe_sql_value(log.get("source_table"))},
            {safe_sql_value(log.get("target_database"))},
            {safe_sql_value(log.get("target_schema"))},
            {safe_sql_value(log.get("target_table"))},
            {safe_sql_value(log.get("source_row_count"))},
            {safe_sql_value(log.get("target_row_count"))},
            {safe_sql_value(log.get("inserted_rows"))},
            {safe_sql_value(log.get("updated_rows"))},
            {safe_sql_value(log.get("load_type"))},
            {safe_sql_value(log.get("cloud_path"))},
            {safe_sql_value(log.get("start_time"))},
            {safe_sql_value(log.get("end_time"))},
            {safe_sql_value(log.get("duration_seconds"))},
            {safe_sql_value(log.get("status"))},
            {safe_sql_value(log.get("error_message"))},
            {safe_sql_value(log.get("watermark_value"))}
        )
        """

        cursor.execute(query)
        logger.info(f"Inserted into Snowflake control table in {control_schema}: {log.get('target_table', 'unknown')}")

    except Exception as e:
        logger.info(f"Error inserting into Snowflake control table: {str(e)}")
        raise Exception(f"Snowflake insert failed: {str(e)}")

    finally:
        try:
            cursor.close()
        except Exception:
            pass


def get_last_successful_run_snowflake(conn, database, schema, table, control_schema="control_schema"):
    cursor = conn.cursor()
    tgt_database = get_target_db(database)

    try:
        query = f"""
        SELECT TO_VARCHAR(MAX(watermark_value), 'YYYY-MM-DD HH24:MI:SS.FF6')
        FROM {tgt_database}.{control_schema}.pipeline_control
        WHERE UPPER(target_database) = UPPER({safe_sql_value(database)})
          AND UPPER(target_schema) = UPPER({safe_sql_value(schema)})
          AND UPPER(target_table) = UPPER({safe_sql_value(table)})
          AND UPPER(status) = 'SUCCESS'
          AND UPPER(COALESCE(load_type, 'INCREMENTAL')) = 'INCREMENTAL'
        """
        cursor.execute(query)
        row = cursor.fetchone()
        return row[0] if row and row[0] else None

    except Exception as e:
        logger.info(f"Error reading Snowflake control watermark: {str(e)}")
        return None

    finally:
        try:
            cursor.close()
        except Exception:
            pass


# ===================================================
# DATABRICKS FUNCTIONS
# ===================================================

def create_control_table_databricks(conn, database, control_schema="control_schema"):
    cursor = conn.cursor()
    Tgt_database = database

    try:
        cursor.execute(f"USE CATALOG {Tgt_database}")
        cursor.execute(f"CREATE SCHEMA IF NOT EXISTS {Tgt_database}.{control_schema}")
        cursor.execute(f"USE SCHEMA {control_schema}")

        query = f"""
        CREATE TABLE IF NOT EXISTS {Tgt_database}.{control_schema}.pipeline_control (
            run_id STRING,
            run_timestamp TIMESTAMP,
            source_system STRING,
            cloud STRING,
            target_system STRING,
            source_database STRING,
            source_schema STRING,
            source_table STRING,
            target_database STRING,
            target_schema STRING,
            target_table STRING,
            source_row_count BIGINT,
            target_row_count BIGINT,
            inserted_rows BIGINT,
            updated_rows BIGINT,
            load_type STRING,
            cloud_path STRING,
            start_time TIMESTAMP,
            end_time TIMESTAMP,
            duration_seconds DOUBLE,
            status STRING,
            error_message STRING,
            watermark_value TIMESTAMP
        )
        USING DELTA
        """

        cursor.execute(query)
        logger.info("Databricks control table ready")

    except Exception as e:
        logger.info(f"Error creating Databricks control table: {str(e)}")
        raise Exception(f"Databricks table creation failed: {str(e)}")

    finally:
        try:
            cursor.close()
        except Exception:
            pass


def insert_table_log_databricks(conn, database, log, control_schema="control_schema"):
    cursor = conn.cursor()
    Tgt_database = database

    try:
        cursor.execute(f"USE CATALOG {Tgt_database}")
        cursor.execute(f"USE SCHEMA {control_schema}")

        query = f""" 
        INSERT INTO {Tgt_database}.{control_schema}.pipeline_control (
            run_id, run_timestamp, source_system, cloud, target_system,
            source_database, source_schema, source_table,
            target_database, target_schema, target_table,
            source_row_count, target_row_count, inserted_rows, updated_rows, load_type, cloud_path,
            start_time, end_time, duration_seconds,
            status, error_message, watermark_value
        )
        VALUES (
            {safe_sql_value(log.get("run_id"))},
            {safe_sql_value(log.get("run_timestamp"))},
            {safe_sql_value(log.get("source_system"))},
            {safe_sql_value(log.get("cloud"))},
            {safe_sql_value(log.get("target_system"))},
            {safe_sql_value(log.get("source_database"))},
            {safe_sql_value(log.get("source_schema"))},
            {safe_sql_value(log.get("source_table"))},
            {safe_sql_value(log.get("target_database"))},
            {safe_sql_value(log.get("target_schema"))},
            {safe_sql_value(log.get("target_table"))},
            {safe_sql_value(log.get("source_row_count"))},
            {safe_sql_value(log.get("target_row_count"))},
            {safe_sql_value(log.get("inserted_rows"))},
            {safe_sql_value(log.get("updated_rows"))},
            {safe_sql_value(log.get("load_type"))},
            {safe_sql_value(log.get("cloud_path"))},
            {safe_sql_value(log.get("start_time"))},
            {safe_sql_value(log.get("end_time"))},
            {safe_sql_value(log.get("duration_seconds"))},
            {safe_sql_value(log.get("status"))},
            {safe_sql_value(log.get("error_message"))},
            {safe_sql_value(log.get("watermark_value"))}
        )
        """
        cursor.execute(query)
        logger.info(f"Inserted into Databricks control table: {log.get('target_table', 'unknown')}")

    except Exception as e:
        logger.info(f"Error inserting into Databricks control table: {str(e)}")
        raise Exception(f"Databricks insert failed: {str(e)}")

    finally:
        try:
            cursor.close()
        except Exception:
            pass


def get_last_successful_run_databricks(conn, database, schema, table, control_schema="control_schema"):
    cursor = conn.cursor()
    tgt_database = database

    try:
        query = f"""
        SELECT MAX(watermark_value)
        FROM {tgt_database}.{control_schema}.pipeline_control
        WHERE lower(target_database) = lower({safe_sql_value(database)})
          AND lower(target_schema) = lower({safe_sql_value(schema)})
          AND lower(target_table) = lower({safe_sql_value(table)})
          AND upper(status) = 'SUCCESS'
          AND upper(coalesce(load_type, 'INCREMENTAL')) = 'INCREMENTAL'
        """
        cursor.execute(query)
        row = cursor.fetchone()
        return row[0] if row and row[0] else None

    except Exception as e:
        logger.info(f"Error reading Databricks control watermark: {str(e)}")
        return None

    finally:
        try:
            cursor.close()
        except Exception:
            pass


# ===================================================
# BIGQUERY FUNCTIONS
# ===================================================

def create_control_table_bigquery(bq_client, dataset_id):
    try:
        table_id = f"{bq_client.project}.control_schema.pipeline_control"

        dataset = bigquery.Dataset(f"{bq_client.project}.control_schema")
        dataset.location = "US"
        bq_client.create_dataset(dataset, exists_ok=True)

        schema = [
            bigquery.SchemaField("run_id", "STRING"),
            bigquery.SchemaField("run_timestamp", "TIMESTAMP"),
            bigquery.SchemaField("source_system", "STRING"),
            bigquery.SchemaField("cloud", "STRING"),
            bigquery.SchemaField("target_system", "STRING"),
            bigquery.SchemaField("source_database", "STRING"),
            bigquery.SchemaField("source_schema", "STRING"),
            bigquery.SchemaField("source_table", "STRING"),
            bigquery.SchemaField("target_database", "STRING"),
            bigquery.SchemaField("target_schema", "STRING"),
            bigquery.SchemaField("target_table", "STRING"),
            bigquery.SchemaField("source_row_count", "INT64"),
            bigquery.SchemaField("target_row_count", "INT64"),
            bigquery.SchemaField("inserted_rows", "INT64"),
            bigquery.SchemaField("updated_rows", "INT64"),
            bigquery.SchemaField("load_type", "STRING"),
            bigquery.SchemaField("cloud_path", "STRING"),
            bigquery.SchemaField("start_time", "TIMESTAMP"),
            bigquery.SchemaField("end_time", "TIMESTAMP"),
            bigquery.SchemaField("duration_seconds", "FLOAT64"),
            bigquery.SchemaField("status", "STRING"),
            bigquery.SchemaField("error_message", "STRING"),
            bigquery.SchemaField("watermark_value", "TIMESTAMP"),
        ]

        table = bigquery.Table(table_id, schema=schema)
        bq_client.create_table(table, exists_ok=True)
        logger.info("BigQuery control table ready")

    except Exception as e:
        logger.info(f"Error creating BigQuery control table: {str(e)}")
        raise Exception(f"BigQuery table creation failed: {str(e)}")


def insert_table_log_bigquery(bq_client, dataset_id, log):
    try:
        table_id = f"{bq_client.project}.control_schema.pipeline_control"

        allowed_fields = {
            "run_id", "run_timestamp", "source_system", "cloud", "target_system",
            "source_database", "source_schema", "source_table",
            "target_database", "target_schema", "target_table",
            "source_row_count", "target_row_count", "inserted_rows", "updated_rows", "load_type", "cloud_path",
            "start_time", "end_time", "duration_seconds", "status",
            "error_message", "watermark_value"
        }

        filtered_log = {
            k: v.isoformat() if isinstance(v, datetime) else v
            for k, v in log.items()
            if k in allowed_fields
        }

        errors = bq_client.insert_rows_json(table_id, [filtered_log])
        if errors:
            logger.error(f"BigQuery insert failed: {errors}")
        else:
            logger.info(f"Inserted into BigQuery control table: {log.get('target_table', 'unknown')}")

    except Exception as e:
        logger.info(f"Error inserting into BigQuery control table: {str(e)}")
        raise Exception(f"BigQuery insert failed: {str(e)}")


def get_last_successful_run_bigquery(bq_client, dataset_id, schema, table):
    try:
        table_id = f"`{bq_client.project}.control_schema.pipeline_control`"
        query = f"""
        SELECT MAX(watermark_value) AS last_run
        FROM {table_id}
        WHERE LOWER(target_database) = LOWER(@database_name)
          AND LOWER(target_schema) = LOWER(@schema_name)
          AND LOWER(target_table) = LOWER(@table_name)
          AND UPPER(status) = 'SUCCESS'
          AND UPPER(COALESCE(load_type, 'INCREMENTAL')) = 'INCREMENTAL'
        """
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("database_name", "STRING", dataset_id),
                bigquery.ScalarQueryParameter("schema_name", "STRING", schema),
                bigquery.ScalarQueryParameter("table_name", "STRING", table),
            ]
        )
        rows = list(bq_client.query(query, job_config=job_config).result())
        return rows[0]["last_run"] if rows and rows[0]["last_run"] else None

    except Exception as e:
        logger.info(f"Error reading BigQuery control watermark: {str(e)}")
        return None


def get_last_successful_run(conn, target, database, schema, table, control_schema="control_schema"):
    if target == "snowflake":
        return get_last_successful_run_snowflake(conn, database, schema, table, control_schema)
    if target == "databricks":
        return get_last_successful_run_databricks(conn, database, schema, table, control_schema)
    if target == "bigquery":
        return get_last_successful_run_bigquery(conn, database, schema, table)
    raise ValueError(f"Unsupported target for control table lookup: {target}")
