from src.pipeline_logger import get_logger
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


def raw_to_target_expression(column, alias="r"):
    prefix = f"{alias}." if alias else ""
    lowered = str(column).lower()
    if "updatedat" in lowered or "timestamp" in lowered or lowered.endswith("_ts"):
        return f"TRY_TO_TIMESTAMP_NTZ({prefix}{column})"
    if "date" in lowered:
        return f"TRY_TO_DATE({prefix}{column})"
    return f"{prefix}{column}"



# --------------------------------------------------
# Snowflake Helper Functions
# --------------------------------------------------

# -----------------------------
# GET COLUMNS FROM RAW
# -----------------------------
def get_table_columns_snowflake(conn, database, schema, table):
    """
    Fetch column names for a given table from Snowflake RAW database.

    Flow:
    1. Build INFORMATION_SCHEMA query
    2. Execute query
    3. Fetch column list
    4. Remove metadata columns
    """

    try:
        raw_db = get_raw_db(database)

        # Build query to fetch column names
        query = f"""
        SELECT COLUMN_NAME
        FROM {raw_db}.INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = '{schema.upper()}'
        AND TABLE_NAME = '{table.upper()}'
        ORDER BY ORDINAL_POSITION
        """

        print("Executing column retrieval query:\n", query)

        # Execute query
        cur = conn.cursor()
        try:
            cur.execute(query)
            cols = [row[0] for row in cur.fetchall()]
        finally:
            # Ensure cursor is closed
            try:
                cur.close()
            except Exception:
                pass

        # Remove raw loader metadata columns. Merge-specific audit columns are
        # filtered later because this helper is used by legacy code too.
        cols = [c for c in cols if c.upper() not in ['LOAD_TS', '__LOAD_TS']]

        print("Columns Found:", cols)
        return cols

    except Exception as e:
        logger.error(f"Error fetching table columns: {str(e)}")
        raise

# --------------------------------------------------
# GENERATE AND RUN MERGE SQL FOR SNOWFLAKE
# --------------------------------------------------
def snowflake_merge_raw_to_target(conn, database, schema, table, primary_keys, columns):
    """
    Perform MERGE from RAW to TGT table.

    Flow:
    1. Prepare audit columns
    2. Build MERGE SQL
    3. Execute MERGE
    4. Fetch result
    5. Truncate RAW table if successful
    """

    try:
        # Normalize primary keys to list
        if isinstance(primary_keys, str):
            primary_keys = [pk.strip() for pk in primary_keys.split(",")]

        print(primary_keys)
        print("pk in merge")

        raw_db = get_raw_db(database)
        tgt_db = get_target_db(database)

        tgt = f'{tgt_db}.{schema}.{table}'
        raw = f'{raw_db}.{schema}.{table}'

        target_columns = [col for col in columns if col.lower() != "file_name"]
        order_column = next(
            (
                col for col in target_columns
                if "updatedat" in col.lower()
                or "lastmodified" in col.lower()
                or "timestamp" in col.lower()
                or col.lower().endswith("date")
            ),
            primary_keys[0]
        )
        order_expression = raw_to_target_expression(order_column, alias=None)

        # Columns to update (excluding primary keys)
        update_cols = [col for col in target_columns if col not in primary_keys]
        update_assignments = [f"t.{col}={raw_to_target_expression(col)}" for col in update_cols]
        update_set = ", ".join(update_assignments)

        insert_cols = ", ".join(target_columns)
        insert_vals = ", ".join([raw_to_target_expression(col) for col in target_columns])

        pk_condition = " AND ".join([f"t.{pk}=r.{pk}" for pk in primary_keys])

        # Build MERGE SQL
        merge_sql = f"""
                    MERGE INTO {tgt} t
                    USING (
                        SELECT *
                        FROM (
                            SELECT *,
                                ROW_NUMBER() OVER (
                                    PARTITION BY {','.join(primary_keys)}
                                    ORDER BY {order_expression} DESC
                                ) rn
                            FROM {raw}
                        )
                        WHERE rn = 1
                    ) r
                    ON {pk_condition}

                    WHEN MATCHED THEN
                        UPDATE SET
                            {update_set}

                    WHEN NOT MATCHED THEN
                        INSERT ({insert_cols})
                        VALUES ({insert_vals});
                    """

        merge_success = False

        # Execute MERGE
        with conn.cursor() as cursor:
            try:
                cursor.execute(merge_sql)
                result = cursor.fetchone()

                # Debug logging
                print(f"RAW MERGE RESULT: {result}")
                logger.info(f"RAW MERGE RESULT: {result}")

                if result is None:
                    raise Exception("MERGE returned no result")

                # Extract inserted & updated counts
                rows_inserted = result[0]
                rows_updated  = result[1]

                logger.info(f"MERGE complete — Inserted: {rows_inserted}, Updated: {rows_updated}")
                print(f"Rows Inserted: {rows_inserted}, Updated: {rows_updated}")

                merge_success = True

            except Exception as e:
                logger.error(f"MERGE FAILED for {table}: {str(e)}")
                print(f"MERGE FAILED for {table}: {str(e)}")
                raise

            # Truncate RAW table only if merge succeeded
            if merge_success:
                truncate_raw_table = truncate_raw_query(database, schema, table)

                try:
                    cursor.execute(truncate_raw_table)

                    logger.info(f"Truncated Table {table} in {raw_db}")
                    print(f"Truncated Table {table} in {raw_db}")

                except Exception as e:
                    logger.error(f"Failed to truncate table {table} in {raw_db}: {str(e)}")
                    print(f"Truncate failed for {table}: {str(e)}")

        return result

    except Exception as e:
        logger.error(f"Error in snowflake_merge_raw_to_target: {str(e)}")
        raise



# --------------------------------------------------
# Databricks Helper Functions
# --------------------------------------------------
# --------------------------------------------------
# GENERATE MERGE SQL FOR DATABRICKS
# --------------------------------------------------
def generate_merge_script_databricks(database, schema, table, primary_keys, columns):
    """
    Generate MERGE SQL script dynamically (no execution).

    Flow:
    1. Prepare audit columns
    2. Build SQL components
    3. Return full MERGE script
    """

    try:
        raw_db = f"{database}_stg.{schema}.{table}"
        tgt_db = f"{database}.{schema}.{table}"

        # Normalize primary keys
        if isinstance(primary_keys, str):
            primary_keys = [pk.strip() for pk in primary_keys.split(",")]

        pk_set = set(pk.lower() for pk in primary_keys)

        # Columns for update
        update_cols = [c for c in columns if c.lower() not in pk_set]
        update_set = ", ".join([f"t.{c}=r.{c}" for c in update_cols])

        # Insert columns and values
        insert_cols = ", ".join(columns)
        insert_vals = ", ".join([f"r.{c}" for c in columns])

        pk_condition = " AND ".join([f"t.{pk}=r.{pk}" for pk in primary_keys])
        partition_by = ", ".join(primary_keys)

        # Build MERGE SQL
        merge_sql = f"""
        MERGE INTO {tgt_db} t
        USING (
            SELECT *
            FROM (
                SELECT *,
                           ROW_NUMBER() OVER (
                           PARTITION BY {partition_by}
                           ORDER BY {partition_by}
                       ) rn
                FROM {raw_db}
            ) x
            WHERE rn = 1
        ) r
        ON {pk_condition}

        WHEN MATCHED THEN
            UPDATE SET
                {update_set}

        WHEN NOT MATCHED THEN
            INSERT ({insert_cols})
            VALUES ({insert_vals});
        """

        return merge_sql

    except Exception as e:
        logger.error(f"Error generating merge script: {str(e)}")
        raise

# --------------------------------------------------
# TRUNCATE RAW TABLE FOR SNOWFLAKE AND DATABRICKS
# --------------------------------------------------
def truncate_raw_query(database, schema, table):
    """
    Build TRUNCATE SQL query for RAW table.
    """

    try:
        raw_db = get_raw_db(database)
        query = f"""
                TRUNCATE TABLE {raw_db}.{schema}.{table};
                """
        return query

    except Exception as e:
        logger.error(f"Error building truncate query: {str(e)}")
        raise



# -----------------------------
# Big Query Helper FUnctions
# -----------------------------

# -----------------------------
# GET COLUMNS FROM RAW
# -----------------------------
def get_columns_BQ(client, project, dataset, table):
    """
    Retrieves business columns from RAW table
    excluding metadata columns.
    """
    try:
        query = f"""
            SELECT column_name
            FROM `{project}.{dataset}.INFORMATION_SCHEMA.COLUMNS`
            WHERE table_name = '{table}'
            ORDER BY ordinal_position
        """

        query_job = client.query(query)

        # Exclude RAW metadata columns
        exclude = {'row_hash', 'file_name'}
        cols = [row.column_name for row in query_job if row.column_name.lower() not in exclude]

        return cols

    except Exception as e:
        logger.info("Error retrieving columns:", str(e))
        raise

# -----------------------------
# GENERATE MERGE SQL
# -----------------------------
def generate_merge_sql_BQ(target_table, staging_table, primary_keys, columns):
    """
    Generates MERGE SQL dynamically using business columns.
    """
    try:
        pk_condition = " AND ".join([f"t.{pk} = s.{pk}" for pk in primary_keys])

        # Update columns (exclude PK)
        update_cols = [c for c in columns if c not in primary_keys]
        update_assignments = [f"t.{c} = s.{c}" for c in update_cols]

        update_set = ",\n        ".join(update_assignments)

        # Insert columns
        insert_cols = columns.copy()

        insert_names = ", ".join(insert_cols)

        insert_vals = [f"s.{c}" for c in columns]

        insert_values = ", ".join(insert_vals)
        merge_sql = f"""
            MERGE `{target_table}` t
            USING (
                SELECT * EXCEPT(rn)
                FROM (
                    SELECT *,
                        ROW_NUMBER() OVER(
                            PARTITION BY {", ".join(primary_keys)}
                            ORDER BY {", ".join(primary_keys)}
                        ) rn
                    FROM `{staging_table}`
                )
                WHERE rn = 1
            ) s
            ON {pk_condition}

            WHEN MATCHED THEN
                UPDATE SET
                    {update_set}

            WHEN NOT MATCHED THEN
                INSERT ({insert_names})
                VALUES ({insert_values})
            """
        return merge_sql

    except Exception as e:
        logger.info("Error generating merge SQL:", str(e))
        raise


# -----------------------------
# TRUNCATE RAW TABLE
# -----------------------------
def truncate_raw_table_BQ(client, table_id):
    """
    Truncates RAW staging table after merge.
    """
    try:
        sql = f"TRUNCATE TABLE `{table_id}`"
        client.query(sql).result()
        logger.info("RAW table truncated")

    except Exception as e:
        logger.info("Error truncating RAW table:", str(e))
        raise


# -----------------------------
# GET TABLE SCHEMA
# -----------------------------
def get_table_schema_BQ(client, table_id):
    """
    Retrieves BigQuery table schema for controlled load.
    """
    try:
        table = client.get_table(table_id)
        return table.schema

    except Exception as e:
        logger.info("Error fetching table schema:", str(e))
        raise


