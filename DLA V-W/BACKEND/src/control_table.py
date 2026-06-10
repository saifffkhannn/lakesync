from src.custom_logger import get_logger
from datetime import datetime
from google.cloud import bigquery
from src.connections import get_snowflake_stage_schema

logger = get_logger()


def get_snowflake_target_database(conn, fallback_database):
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT CURRENT_DATABASE()")
        current_database = cursor.fetchone()[0]
        return current_database or fallback_database
    except Exception:
        return fallback_database
    finally:
        try:
            cursor.close()
        except Exception:
            pass


def normalize_snowflake_target_database_name(database_name):
    if str(database_name).upper().endswith("_TGT"):
        return str(database_name)

    return f"{database_name}_tgt"


def get_snowflake_base_database_name(database_name):
    database_name = str(database_name)

    if database_name.upper().endswith("_TGT"):
        return database_name[:-4]

    return database_name





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
            return f"'{value.strftime('%Y-%m-%d %H:%M:%S')}'"

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

def create_control_table_snowflake(conn, database):
    """
    Creates PipelineRunControl table in Snowflake target database.

    Steps:
    1. Append _tgt to database
    2. Execute CREATE TABLE IF NOT EXISTS
    3. Close cursor safely
    """

    cursor = conn.cursor()
    
    target_database = get_snowflake_target_database(conn, database)
    base_database = get_snowflake_base_database_name(target_database)
    Tgt_database = normalize_snowflake_target_database_name(target_database)
    control_schema = get_snowflake_stage_schema(base_database)

    try:
        query = f"""
        CREATE SCHEMA IF NOT EXISTS {Tgt_database}.{control_schema}
        """
        cursor.execute(query)

        query = f"""
        CREATE TABLE IF NOT EXISTS {Tgt_database}.{control_schema}.PipelineRunControl (
            run_id STRING,
            run_timestamp TIMESTAMP,
            source_system STRING,
            cloud STRING,
            target_system STRING,
            database_name STRING,
            schema_name STRING,
            table_name STRING,
            source_row_count INTEGER,
            target_row_count INTEGER,
            load_type STRING,
            cloud_path STRING,
            start_time TIMESTAMP,
            end_time TIMESTAMP,
            duration_seconds FLOAT,
            status STRING,
            error_message STRING
        )
        """

        cursor.execute(query)

        required_columns = [
            ("run_id", "STRING"),
            ("run_timestamp", "TIMESTAMP"),
            ("source_system", "STRING"),
            ("cloud", "STRING"),
            ("target_system", "STRING"),
            ("database_name", "STRING"),
            ("schema_name", "STRING"),
            ("table_name", "STRING"),
            ("source_row_count", "INTEGER"),
            ("target_row_count", "INTEGER"),
            ("load_type", "STRING"),
            ("cloud_path", "STRING"),
            ("start_time", "TIMESTAMP"),
            ("end_time", "TIMESTAMP"),
            ("duration_seconds", "FLOAT"),
            ("status", "STRING"),
            ("error_message", "STRING"),
        ]

        table_name = f"{Tgt_database}.{control_schema}.PipelineRunControl"
        for column_name, column_type in required_columns:
            cursor.execute(
                f"ALTER TABLE {table_name} "
                f"ADD COLUMN IF NOT EXISTS {column_name} {column_type}"
            )

        logger.info("Snowflake control table ready")

    except Exception as e:
        # Capture any DDL execution issues
        logger.info(f"Error creating Snowflake control table: {str(e)}")
        raise Exception(f"Snowflake table creation failed: {str(e)}")

    finally:
        # Ensure cursor is always closed
        try:
            cursor.close()
        except Exception as e:
            logger.info(f"Error closing Snowflake cursor: {str(e)}")


def insert_table_log_snowflake(conn, database, log):
    """
    Inserts a log record into Snowflake control table.

    Notes:
    - Uses safe_sql_value for SQL safety
    - Only inserts predefined control fields
    """

    cursor = conn.cursor()
    target_database = get_snowflake_target_database(conn, database)
    base_database = get_snowflake_base_database_name(target_database)
    Tgt_database = normalize_snowflake_target_database_name(target_database)
    control_schema = get_snowflake_stage_schema(base_database)

    try:
        query = f"""
        INSERT INTO {Tgt_database}.{control_schema}.PipelineRunControl (
            run_id, run_timestamp, source_system, cloud, target_system,
            database_name, schema_name, table_name,
            source_row_count, target_row_count, load_type, cloud_path,
            start_time, end_time, duration_seconds,
            status, error_message
        )
        VALUES (
            {safe_sql_value(log.get("run_id"))},
            {safe_sql_value(log.get("run_timestamp"))},
            {safe_sql_value(log.get("source_system"))},
            {safe_sql_value(log.get("cloud"))},
            {safe_sql_value(log.get("target_system"))},
            {safe_sql_value(log.get("database_name"))},
            {safe_sql_value(log.get("schema_name"))},
            {safe_sql_value(log.get("table_name"))},
            {safe_sql_value(log.get("source_row_count"))},
            {safe_sql_value(log.get("target_row_count"))},
            {safe_sql_value(log.get("load_type"))},
            {safe_sql_value(log.get("cloud_path"))},
            {safe_sql_value(log.get("start_time"))},
            {safe_sql_value(log.get("end_time"))},
            {safe_sql_value(log.get("duration_seconds"))},
            {safe_sql_value(log.get("status"))},
            {safe_sql_value(log.get("error_message"))}
        )
        """

        cursor.execute(query)
        logger.info(f"Inserted into Snowflake control table: {log['table_name']}")

    except Exception as e:
        logger.info(f"Error inserting into Snowflake control table: {str(e)}")
        raise Exception(f"Snowflake insert failed: {str(e)}")

    finally:
        try:
            cursor.close()
        except Exception as e:
            logger.info(f"Error closing Snowflake cursor: {str(e)}")


# ===================================================
# DATABRICKS FUNCTIONS
# ===================================================

def create_control_table_databricks(conn, database):
    """
    Creates Delta control table in Databricks.

    Steps:
    1. Switch catalog
    2. Create schema if not exists
    3. Create Delta table
    """

    cursor = conn.cursor()
    Tgt_database = f"{database}_tgt"
    control_schema = f"{database}_stg"

    try:
        cursor.execute(f"USE CATALOG {Tgt_database}")
        cursor.execute(f"CREATE SCHEMA IF NOT EXISTS {Tgt_database}.{control_schema}")
        cursor.execute(f"USE SCHEMA {control_schema}")

        query = f"""
        CREATE TABLE IF NOT EXISTS {Tgt_database}.{control_schema}.PipelineRunControl (
            run_id STRING,
            run_timestamp TIMESTAMP,
            source_system STRING,
            cloud STRING,
            target_system STRING,
            database_name STRING,
            schema_name STRING,
            table_name STRING,
            source_row_count BIGINT,
            target_row_count BIGINT,
            load_type STRING,
            cloud_path STRING,
            start_time TIMESTAMP,
            end_time TIMESTAMP,
            duration_seconds DOUBLE,
            status STRING,
            error_message STRING
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
        except Exception as e:
            logger.info(f"Error closing Databricks cursor: {str(e)}")


def insert_table_log_databricks(conn, database, log):
    """
    Inserts a log record into Databricks Delta control table.
    """

    cursor = conn.cursor()
    Tgt_database = f"{database}_tgt"
    control_schema = f"{database}_stg"

    try:
        cursor.execute(f"USE CATALOG {Tgt_database}")
        cursor.execute(f"USE SCHEMA {control_schema}")

        query = f""" 
        INSERT INTO {Tgt_database}.{control_schema}.PipelineRunControl (
            run_id, run_timestamp, source_system, cloud, target_system,
            database_name, schema_name, table_name,
            source_row_count, target_row_count,load_type, cloud_path,
            start_time, end_time, duration_seconds,
            status, error_message
        )
        VALUES (
            {safe_sql_value(log.get("run_id"))},
            {safe_sql_value(log.get("run_timestamp"))},
            {safe_sql_value(log.get("source_system"))},
            {safe_sql_value(log.get("cloud"))},
            {safe_sql_value(log.get("target_system"))},
            {safe_sql_value(log.get("database_name"))},
            {safe_sql_value(log.get("schema_name"))},
            {safe_sql_value(log.get("table_name"))},
            {safe_sql_value(log.get("source_row_count"))},
            {safe_sql_value(log.get("target_row_count"))},
            {safe_sql_value(log.get("load_type"))},
            {safe_sql_value(log.get("cloud_path"))},
            {safe_sql_value(log.get("start_time"))},
            {safe_sql_value(log.get("end_time"))},
            {safe_sql_value(log.get("duration_seconds"))},
            {safe_sql_value(log.get("status"))},
            {safe_sql_value(log.get("error_message"))}
        )
        """
        cursor.execute(query)

        logger.info(f"Inserted into Databricks control table: {log['table_name']}")

    except Exception as e:
        logger.info(f"Error inserting into Databricks control table: {str(e)}")
        raise Exception(f"Databricks insert failed: {str(e)}")

    finally:
        try:
            cursor.close()
        except Exception as e:
            logger.info(f"Error closing Databricks cursor: {str(e)}")


# ===================================================
# BIGQUERY FUNCTIONS
# ===================================================

def create_control_table_bigquery(bq_client, dataset_id):
    """
    Creates dataset + control table in BigQuery.

    Steps:
    1. Create dataset if not exists
    2. Define schema
    3. Create table
    """

    try:
        dataset_id_tgt = f"{dataset_id.lower()}_tgt"
        table_id = f"{bq_client.project}.{dataset_id_tgt}.PipelineRunControl"

        dataset = bigquery.Dataset(f"{bq_client.project}.{dataset_id_tgt}")
        dataset.location = "US"

        bq_client.create_dataset(dataset, exists_ok=True)

        # Define schema (unchanged)
        schema = [
            bigquery.SchemaField("run_id", "STRING"),
            bigquery.SchemaField("run_timestamp", "TIMESTAMP"),
            bigquery.SchemaField("source_system", "STRING"),
            bigquery.SchemaField("cloud", "STRING"),
            bigquery.SchemaField("target_system", "STRING"),
            bigquery.SchemaField("database_name", "STRING"),
            bigquery.SchemaField("schema_name", "STRING"),
            bigquery.SchemaField("table_name", "STRING"),
            bigquery.SchemaField("source_row_count", "INT64"),
            bigquery.SchemaField("target_row_count", "INT64"),
            bigquery.SchemaField("load_type", "STRING"),
            bigquery.SchemaField("cloud_path", "STRING"),
            bigquery.SchemaField("start_time", "TIMESTAMP"),
            bigquery.SchemaField("end_time", "TIMESTAMP"),
            bigquery.SchemaField("duration_seconds", "FLOAT64"),
            bigquery.SchemaField("status", "STRING"),
            bigquery.SchemaField("error_message", "STRING"),
        ]

        table = bigquery.Table(table_id, schema=schema)
        bq_client.create_table(table, exists_ok=True)

        logger.info("BigQuery control table ready")

    except Exception as e:
        logger.info(f"Error creating BigQuery control table: {str(e)}")
        raise Exception(f"BigQuery table creation failed: {str(e)}")


def insert_table_log_bigquery(bq_client, dataset_id, log):
    """
    Inserts log into BigQuery control table.

    Notes:
    - Filters only allowed fields
    - Converts datetime → ISO string
    """

    try:
        dataset_id_tgt = f"{dataset_id.lower()}_tgt"
        table_id = f"{bq_client.project}.{dataset_id_tgt}.PipelineRunControl"

        allowed_fields = {
            "run_id", "run_timestamp", "source_system", "cloud", "target_system",
            "database_name", "schema_name", "table_name", "source_row_count",
            "target_row_count", "load_type", "cloud_path", "start_time",
            "end_time", "duration_seconds", "status", "error_message"
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
            logger.info(f"Inserted into BigQuery control table: {filtered_log.get('table_name')}")

    except Exception as e:
        logger.info(f"Error inserting into BigQuery control table: {str(e)}")
        raise Exception(f"BigQuery insert failed: {str(e)}")
