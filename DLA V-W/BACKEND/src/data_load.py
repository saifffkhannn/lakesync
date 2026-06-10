"""
Data Load Module

Handles loading parquet data from cloud storage into:
    - Databricks Delta Tables
    - Snowflake Tables
"""
from datetime import datetime
from src.parse_config import parse_config
from src.custom_logger import get_logger
from google.cloud import bigquery
from src.connections import get_snowflake_stage_schema
from src.helper_functions import (
    get_table_columns_snowflake, 
    snowflake_merge_raw_to_target, 
    generate_merge_script_databricks,
    truncate_raw_query, 
    get_columns_BQ,
    generate_merge_sql_BQ,
    truncate_raw_table_BQ,
    get_table_schema_BQ
    )
logger = get_logger()


# -------------------------------------------------------------------
# LOAD FROM S3 TO DATABRICKS
# -------------------------------------------------------------------

def load_s3_to_databricks(
    target_conn,
    config_path: str,
    schema: str,
    table_name: str,
    folder_structure,
    primary_keys
) -> bool:
    """
    Load Parquet data from S3 into Databricks Delta table using COPY INTO.

    Args:
        target_conn : Target Connection
        config_path (str): Path to config file
        schema (str): Databricks schema
        table_name (str): Table name
        primary_keys : primary keys from metadata file

    Returns:
        bool: True if load successful
    """
    try:
        # --------------------------------------------------
        # Load config and construct paths
        # --------------------------------------------------
        try:
            config = parse_config(config_path)

            catalog = config["databricks"]["catalog"]

            aws_cfg = config["aws"]
            s3_bucket = aws_cfg["s3_bucket_name"]
            s3_url = f"s3://{s3_bucket}/{folder_structure}/"

        except Exception as e:
            logger.error(f"Config parsing failed | Error: {str(e)}")
            raise

        # --------------------------------------------------
        # Prepare table names (sanitize invalid chars)
        # --------------------------------------------------
        raw_catalog = f"{catalog}_raw"
        tgt_catalog = f"{catalog}_tgt"

        safe_table = table_name.replace("/", "_")
        full_raw_table = f"{raw_catalog}.{schema}.{safe_table}"

        # --------------------------------------------------
        # COPY INTO (load data into RAW table)
        # --------------------------------------------------
        copy_sql = f"""
        COPY INTO {full_raw_table}
        FROM '{s3_url}'
        FILEFORMAT = PARQUET
        FORMAT_OPTIONS ('recursiveFileLookup' = 'true')
        COPY_OPTIONS ('mergeSchema' = 'true','force' = 'true');
        """

        logger.info(f"Loading data into Databricks table {full_raw_table}")

        conn = target_conn

        try:
            cursor = conn.cursor()
            cursor.execute(copy_sql)
            result = cursor.fetchall()
        except Exception as e:
            logger.error(f"COPY INTO execution failed | Error: {str(e)}")
            raise

        # --------------------------------------------------
        # Validate load results
        # --------------------------------------------------
        if not result:
            logger.error("COPY INTO returned no result")
            raise Exception("COPY INTO returned no result")

        total_rows = 0

        for row in result:
            file_name = row[0]
            rows_loaded = row[1]

            logger.info(f"File: {file_name}, Rows Loaded: {rows_loaded}")

            if rows_loaded == 0:
                logger.error(f"No rows loaded for file: {file_name}")
                raise Exception(f"No rows loaded for file: {file_name}")

            total_rows += rows_loaded

        raw_db = f"{catalog}_raw.{schema}.{safe_table}"

        # --------------------------------------------------
        # Get column list for merge
        # --------------------------------------------------
        try:
            cursor.execute(f"DESCRIBE {raw_db}")
            cols = [row[0] for row in cursor.fetchall()]
            cols = [c for c in cols if c and not c.startswith('#')]
        except Exception as e:
            logger.error(f"Failed to fetch columns from RAW table | Error: {str(e)}")
            raise

        # --------------------------------------------------
        # MERGE RAW → TARGET
        # --------------------------------------------------
        merge_success = False

        try:
            merge_sql = generate_merge_script_databricks(catalog, schema, safe_table, primary_keys, cols)

            logger.info("Running MERGE operation...")
            cursor.execute(merge_sql)

            merge_success = True

        except Exception as e:
            logger.error(f"MERGE FAILED for {safe_table} | Error: {str(e)}")
            raise

        # --------------------------------------------------
        # Truncate RAW table after successful merge
        # --------------------------------------------------
        if merge_success:
            try:
                truncate_raw = truncate_raw_query(catalog, schema, safe_table)
                cursor.execute(truncate_raw)

                logger.info(f"Truncated RAW table: {safe_table}")

            except Exception as e:
                logger.error(f"Failed to truncate RAW table | Error: {str(e)}")

        # --------------------------------------------------
        #  Final logging
        # --------------------------------------------------
        logger.info({
            "event": "databricks_load_complete",
            "table": full_raw_table,
            "rows_loaded": total_rows,
            "status": "SUCCESS"
        })

        logger.info("Azure Databricks load completed successfully")
        return True

    except Exception as e:
        logger.error(f"Databricks load failed | Error: {str(e)}")
        raise

# -------------------------------------------------------------------
# LOAD FROM AZURE TO DATABRICKS
# -------------------------------------------------------------------
def load_azure_to_databricks(
    target_conn,
    config_path: str,
    schema: str,
    table_name: str,
    folder_structure: str,
    primary_keys
) -> bool:
    """
    Load Parquet data from Azure ADLS into Databricks Delta table.

    Args:
        config_path (str)
        schema (str)
        table_name (str)
        folder_structure (str)

    Returns:
        bool
    """
    try:
        # --------------------------------------------------
        # Load configuration (Databricks + Azure details)
        # --------------------------------------------------
        try:
            config = parse_config(config_path)

            catalog = config["databricks"]["catalog"]
            container = config["azure"]["container_name"]
            storage_account = config["azure"]["storage_account"]

        except Exception as e:
            logger.error(f"Config parsing failed | Error: {str(e)}")
            raise

        # --------------------------------------------------
        # Prepare table and Azure path
        # --------------------------------------------------
        safe_table = table_name.replace("/", "_")  # sanitize table name
        full_table = f"{catalog}_raw.{schema}.{safe_table}"

        azure_path = (
            f"abfss://{container}@{storage_account}.dfs.core.windows.net/"
            f"{folder_structure}/"
        )

        # --------------------------------------------------
        # Build COPY INTO SQL
        # --------------------------------------------------
        copy_sql = f"""
        COPY INTO {full_table}
        FROM '{azure_path}'
        FILEFORMAT = PARQUET
        FORMAT_OPTIONS ('recursiveFileLookup' = 'true')
        COPY_OPTIONS ('mergeSchema' = 'true','force' = 'true')
        """

        logger.info(f"Loading Azure data into Databricks table {full_table}")
        logger.info(f"Azure Path: {azure_path}")

        conn = target_conn

        # --------------------------------------------------
        # Execute COPY INTO (load data)
        # --------------------------------------------------
        try:
            cursor = conn.cursor()
            cursor.execute(copy_sql)
            result = cursor.fetchall()
        except Exception as e:
            logger.error(f"COPY INTO execution failed | Error: {str(e)}")
            raise

        # --------------------------------------------------
        # Validate load results (critical check)
        # --------------------------------------------------
        if not result:
            logger.error("COPY INTO returned no result")
            raise Exception("COPY INTO returned no result")

        total_rows = 0

        for row in result:
            file_name = row[0]
            rows_loaded = row[1]

            logger.info(f"File: {file_name}, Rows Loaded: {rows_loaded}")

            if rows_loaded == 0:
                logger.error(f"No rows loaded for file: {file_name}")
                raise Exception(f"No rows loaded for file: {file_name}")

            total_rows += rows_loaded

        raw_db = f"{catalog}_raw.{schema}.{safe_table}"

        # --------------------------------------------------
        # Fetch columns for merge
        # --------------------------------------------------
        try:
            cursor.execute(f"DESCRIBE {raw_db}")
            cols = [row[0].lower() for row in cursor.fetchall()]
            cols = [c for c in cols if c and not c.startswith('#')]
        except Exception as e:
            logger.error(f"Failed to fetch columns from RAW table | Error: {str(e)}")
            raise

        # --------------------------------------------------
        # MERGE RAW → TARGET
        # --------------------------------------------------
        merge_success = False

        try:
            merge_sql = generate_merge_script_databricks(
                catalog, schema, safe_table, primary_keys, cols
            )

            logger.info("Merging Raw and Target Tables...")
            logger.info("Running MERGE...")
            print("Running MERGE...")

            cursor.execute(merge_sql)
            logger.info("MERGE Completed Successfully")
            merge_success = True

        except Exception as e:
            logger.error(f"MERGE FAILED for {safe_table} | Error: {str(e)}")
            print(f"❌ MERGE FAILED for {safe_table}: {str(e)}")
            raise

        # --------------------------------------------------
        #  Truncate RAW table after successful merge
        # --------------------------------------------------
        if merge_success:
            truncate_raw = truncate_raw_query(catalog, schema, safe_table)

            try:
                cursor.execute(truncate_raw)
                logger.info(f"Truncated Table {safe_table} in {raw_db}")
                print(f"Truncated Table {safe_table} in {raw_db}")

            except Exception as e:
                logger.error(f"Failed to truncate table {safe_table} in {raw_db} | Error: {str(e)}")
                print(f"❌ Truncate failed for {safe_table}: {str(e)}")

        # --------------------------------------------------
        #  Final success logging
        # --------------------------------------------------
        logger.info({
            "event": "databricks_load_complete",
            "table": full_table,
            "rows_loaded": total_rows,
            "status": "SUCCESS"
        })

        logger.info("Databricks load completed successfully")
        return True

    except Exception as e:
        logger.error(f"Azure Databricks load failed | Error: {str(e)}")
        raise

    finally:
        # --------------------------------------------------
        #  Ensure cursor is closed safely
        # --------------------------------------------------
        try:
            if cursor:
                cursor.close()
        except Exception as e:
            logger.error(f"Failed to close cursor | Error: {str(e)}")



# -------------------------------------------------------------------
# LOAD FROM S3 TO SNOWFLAKE
# -------------------------------------------------------------------
def load_s3_to_snowflake(
    target_conn,
    config_path: str,
    schema: str,
    table_name: str,
    folder_structure,
    primary_keys
) -> bool:
    """
    Load Parquet data from S3 into Snowflake using COPY INTO.

    Args:
        config_path (str)
        schema (str)
        table_name (str)

    Returns:
        bool
    """
    try:
        # --------------------------------------------------
        # Load configuration (Snowflake + stage details)
        # --------------------------------------------------
        try:
            config = parse_config(config_path)
            sf_cfg = config["snowflake"]

            database = sf_cfg["database"]
            stg_schema = get_snowflake_stage_schema(database)

        except Exception as e:
            logger.error(f"Config parsing failed | Error: {str(e)}")
            raise

        # --------------------------------------------------
        # Prepare stage and table names
        # --------------------------------------------------
        stage_name = f"{database}_tgt.{stg_schema}.EXTERNAL_AWS_STAGE"

        safe_table = table_name.replace("/", "_")  # sanitize table name
        full_table = f"{database}_raw.{schema}.{safe_table}"

        # Stage path inside Snowflake stage
        stage_path = f"{stage_name}/{folder_structure}"

        # --------------------------------------------------
        # Build COPY INTO SQL (S3 → Snowflake)
        # --------------------------------------------------
        copy_sql = f"""
        COPY INTO {full_table}
        FROM @{stage_path}
        FILE_FORMAT = (TYPE = PARQUET)
        MATCH_BY_COLUMN_NAME = CASE_INSENSITIVE
        FORCE = TRUE
        """

        logger.info(f"Loading data into Snowflake table {full_table}")

        conn = target_conn

        # --------------------------------------------------
        # Execute COPY INTO
        # --------------------------------------------------
        try:
            with conn.cursor() as cursor:
                cursor.execute(copy_sql)
                result = cursor.fetchall()
                logger.info(f"COPY INTO raw result: {result}")
        except Exception as e:
            logger.error(f"COPY INTO execution failed | Error: {str(e)}")
            raise

        # --------------------------------------------------
        # Validate COPY INTO results (critical)
        # --------------------------------------------------
        if not result:
            logger.error("COPY INTO returned no result")
            raise Exception("COPY INTO returned no result")

        total_rows_loaded = 0

        for row in result:

            row_len = len(row)

            file_name = row[0] if row_len > 0 else None
            status = row[1] if row_len > 1 else None
            rows_parsed = row[2] if row_len > 2 else 0
            rows_loaded = row[3] if row_len > 3 else 0
            error_limit = row[4] if row_len > 4 else None
            errors_seen = row[5] if row_len > 5 else 0
            first_error = row[6] if row_len > 6 else None
            first_error_line = row[7] if row_len > 7 else None
            first_error_column = row[8] if row_len > 8 else None

            logger.info(
                f"File: {file_name}, Status: {status}, "
                f"Parsed: {rows_parsed}, Loaded: {rows_loaded}, "
                f"ErrorLimit: {error_limit}, ErrorsSeen: {errors_seen}"
            )

            # Fail if no rows loaded (critical issue)
            if rows_loaded == 0:
                logger.error(f"Critical failure: No rows loaded for {file_name}")
                raise Exception(f"Critical failure: No rows loaded for {file_name}")

            if errors_seen and errors_seen > 0:
                logger.error(
                    f"Snowflake COPY reported {errors_seen} row errors for {file_name}. "
                    f"First error: {first_error} | "
                    f"Line: {first_error_line} | Column: {first_error_column}"
                )
                raise Exception(
                    f"Snowflake COPY row errors detected for {file_name}: {first_error}"
                )

            total_rows_loaded += rows_loaded

        # --------------------------------------------------
        # Fetch table columns (used for merge logic)
        # --------------------------------------------------
        try:
            columns = get_table_columns_snowflake(conn, database, schema, safe_table)
        except Exception as e:
            logger.error(f"Failed to fetch table columns | Error: {str(e)}")
            raise

        # --------------------------------------------------
        # MERGE RAW → TARGET
        # --------------------------------------------------
        try:
            snowflake_merge_raw_to_target(
                conn, database, schema, safe_table, primary_keys, columns
            )
            logger.info("Merge Completed Successfully")
        except Exception as e:
            logger.error(f"MERGE failed for {safe_table} | Error: {str(e)}")
            raise

        # --------------------------------------------------
        # Final success logging
        # --------------------------------------------------
        logger.info({
            "event": "snowflake_load_complete",
            "table": full_table,
            "rows_loaded": total_rows_loaded,
            "status": "SUCCESS"
        })

        logger.info("Snowflake Loading completed successfully")
        return True

    except Exception as e:
        logger.error(f"Snowflake load failed | Error: {str(e)}")
        raise


# -------------------------------------------------------------------
# LOAD FROM AZURE TO SNOWFLAKE
# -------------------------------------------------------------------
def load_azure_to_snowflake(
    target_conn,
    config_path: str,
    schema: str,
    table_name: str,
    folder_structure,
    primary_keys
) -> bool:
    """
    Load Parquet data from Azure ADLS into Snowflake table.

    Args:
        target_conn
        config_path (str)
        schema (str)
        table_name (str)
        primary_keys
    Returns:
        bool
    """

    logger = get_logger()

    try:
        # --------------------------------------------------
        # Load configuration (Snowflake + Azure stage details)
        # --------------------------------------------------
        try:
            config = parse_config(config_path)
            sf_cfg = config["snowflake"]

            database = sf_cfg["database"]
            stg_schema = get_snowflake_stage_schema(database)

        except Exception as e:
            logger.error(f"Config parsing failed | Error: {str(e)}")
            raise

        # --------------------------------------------------
        # Prepare stage and table names
        # --------------------------------------------------
        stage_name = f"{database}_tgt.{stg_schema}.EXTERNAL_AZURE_STAGE"
        
        # Clean table name to avoid invalid characters
        safe_table = table_name.replace("/", "_")
        full_table = f"{database}_raw.{schema}.{safe_table}"

        # Stage path inside Snowflake stage
        stage_path = f"{stage_name}/{folder_structure}"

        # --------------------------------------------------
        # Build COPY INTO SQL (Azure → Snowflake)
        # --------------------------------------------------
        copy_sql = f"""
        COPY INTO {full_table}
        FROM @{stage_path}
        FILE_FORMAT = (TYPE = PARQUET)
        MATCH_BY_COLUMN_NAME = CASE_INSENSITIVE
        FORCE = TRUE
        """

        logger.info(f"Loading Azure data into Snowflake table {full_table}")
        logger.info(f"Stage Path: @{stage_path}")

        conn = target_conn

        # --------------------------------------------------
        # Execute COPY INTO
        # --------------------------------------------------
        try:
            with conn.cursor() as cursor:
                cursor.execute(copy_sql)
                result = cursor.fetchall()
                logger.info(f"COPY INTO raw result: {result}")
        except Exception as e:
            logger.error(f"COPY INTO execution failed | Error: {str(e)}")
            raise

        # --------------------------------------------------
        # Validate COPY results (critical      # --------------------------------------------------
        if not result:
            logger.error("COPY INTO returned no result")
            raise Exception("COPY INTO returned no result")

        total_rows_loaded = 0

        for row in result:
            # Snowflake COPY result commonly returns:
            # file, status, rows_parsed, rows_loaded, error_limit,
            # errors_seen, first_error, first_error_line,
            # first_error_character, first_error_column_name
            file_name = row[0]
            status = row[1]
            rows_parsed = row[2]
            rows_loaded = row[3]
            error_limit = row[4] if len(row) > 4 else None
            errors_seen = row[5] if len(row) > 5 else 0
            first_error = row[6] if len(row) > 6 else None
            first_error_line = row[7] if len(row) > 7 else None
            first_error_column = row[9] if len(row) > 9 else None

            logger.info(
                f"File: {file_name}, Status: {status}, "
                f"Parsed: {rows_parsed}, Loaded: {rows_loaded}, "
                f"ErrorLimit: {error_limit}, ErrorsSeen: {errors_seen}"
            )

            # Fail if no data loaded (critical issue)
            if rows_loaded == 0:
                logger.error(f"Critical failure: No rows loaded for {file_name}")
                raise Exception(f"Critical failure: No rows loaded for {file_name}")

            if errors_seen and errors_seen > 0:
                logger.error(
                    f"Snowflake COPY reported {errors_seen} row errors for {file_name}. "
                    f"First error: {first_error} | "
                    f"Line: {first_error_line} | Column: {first_error_column}"
                )
                raise Exception(
                    f"Snowflake COPY row errors detected for {file_name}: {first_error}"
                )

            total_rows_loaded += rows_loaded

        # --------------------------------------------------
        # Fetch table columns for merge
        # --------------------------------------------------
        try:
            columns = get_table_columns_snowflake(conn, database, schema, safe_table)
        except Exception as e:
            logger.error(f"Failed to fetch table columns | Error: {str(e)}")
            raise

        # --------------------------------------------------
        # MERGE RAW → TARGET
        # --------------------------------------------------
        try:
            snowflake_merge_raw_to_target(
                conn, database, schema, safe_table, primary_keys, columns
            )
            logger.info("Merge Completed Successfully")
        except Exception as e:
            logger.error(f"MERGE failed for {safe_table} | Error: {str(e)}")
            raise

        # --------------------------------------------------
        # Final success logging
        # --------------------------------------------------
        logger.info({
            "event": "snowflake_load_complete",
            "table": full_table,
            "rows_loaded": total_rows_loaded,
            "status": "SUCCESS"
        })

        logger.info("Snowflake Loading completed successfully")
        return True

    except Exception as e:
        logger.error(f"Snowflake load failed | Error: {str(e)}")
        raise



# -----------------------------
# LOAD FROM GCS TO BIGQUERY
# -----------------------------
def load_gcs_to_bigquery(
        target_conn,
        config_path,
        dataset, 
        schema, 
        table, 
        folder_structure,
        primary_keys
        ):
    """
    Main pipeline:
    Load Parquet files from GCS -> RAW table
    Merge RAW -> TARGET
    Truncate RAW
    """



    try:
        # --------------------------------------------------
        # Initialize BigQuery client
        # --------------------------------------------------
        client = target_conn

        # --------------------------------------------------
        # Load config and project details
        # --------------------------------------------------
        try:
            cfg = parse_config(config_path)
            project = cfg["bigquery"]["project"]
        except Exception as e:
            logger.info(f"Config parsing failed: {str(e)}")
            raise

        # --------------------------------------------------
        # Prepare RAW and TARGET table names
        # --------------------------------------------------
        raw_table = f"{project}.{dataset.lower()}_raw.{table.lower()}"
        tgt_table = f"{project}.{dataset.lower()}_tgt.{table.lower()}"


        bucket_name = cfg["gcp"]["bucket_name"]
        gcs_path = f"gs://{bucket_name}/{folder_structure}/*.parquet"

        logger.info("Starting Load Process")
        logger.info(f"GCS Path:", gcs_path)

        # --------------------------------------------------
        # Fetch RAW table schema (ensures schema consistency)
        # --------------------------------------------------
        try:
            schema = get_table_schema_BQ(client, raw_table)
        except Exception as e:
            logger.info(f"Failed to fetch RAW table schema: {str(e)}")
            raise

        # --------------------------------------------------
        # Configure load job (Parquet → BigQuery)
        # --------------------------------------------------
        job_config = bigquery.LoadJobConfig(
            source_format=bigquery.SourceFormat.PARQUET,
            write_disposition=bigquery.WriteDisposition.WRITE_APPEND,
            schema=schema,
            ignore_unknown_values=True
        )

        # --------------------------------------------------
        # Load data into RAW table
        # --------------------------------------------------
        try:
            logger.info(f"Loading data into RAW table: {raw_table}")

            load_job = client.load_table_from_uri(
                gcs_path,
                raw_table,
                job_config=job_config
            )

            load_job.result()  # wait for job completion

            logger.info("COPY INTO RAW Completed")

        except Exception as e:
            logger.info(f"RAW load failed: {str(e)}")
            raise

        # --------------------------------------------------
        # Fetch business columns (exclude metadata)
        # --------------------------------------------------
        try:
            columns = get_columns_BQ(
                client,
                project,
                f"{dataset.lower()}_raw",
                table.lower()
            )
        except Exception as e:
            logger.info(f"Failed to fetch columns: {str(e)}")
            raise

        # --------------------------------------------------
        # Generate MERGE SQL dynamically
        # --------------------------------------------------
        try:
            merge_sql = generate_merge_sql_BQ(
                tgt_table,
                raw_table,
                primary_keys,
                columns
            )
            logger.info(merge_sql)
        except Exception as e:
            logger.info(f"Failed to generate MERGE SQL: {str(e)}")
            raise

        # --------------------------------------------------
        # Execute MERGE (RAW → TARGET)
        # --------------------------------------------------
        try:
            logger.info("Running MERGE into TARGET")
            client.query(merge_sql).result()
        except Exception as e:
            logger.info(f"MERGE execution failed: {str(e)}")
            raise

        # --------------------------------------------------
        #  Truncate RAW table after successful merge
        # --------------------------------------------------
        try:
            truncate_raw_table_BQ(client, raw_table)
        except Exception as e:
            logger.info(f"Failed to truncate RAW table: {str(e)}")
            raise

        

        logger.info("MERGE Completed Successfully")

    except Exception as e:
        logger.info(f"Pipeline failed: {str(e)}")
        raise

