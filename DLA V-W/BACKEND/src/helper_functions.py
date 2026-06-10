import os
from src.custom_logger import get_logger

logger = get_logger()



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
        raw_db = f"{database}_RAW"

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

        print("Columns Found:", cols)
        return cols

    except Exception as e:
        logger.error(f"Error fetching table columns: {str(e)}")
        raise


def get_table_schema_snowflake(conn, database, schema, table, table_role="RAW"):
    try:
        db_name = f"{database}_{table_role.upper()}"

        query = f"""
        SELECT COLUMN_NAME, DATA_TYPE
        FROM {db_name}.INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = '{schema.upper()}'
        AND TABLE_NAME = '{table.upper()}'
        ORDER BY ORDINAL_POSITION
        """

        cur = conn.cursor()
        try:
            cur.execute(query)
            return cur.fetchall()
        finally:
            try:
                cur.close()
            except Exception:
                pass

    except Exception as e:
        logger.error(f"Error fetching table schema: {str(e)}")
        raise


def _build_snowflake_cast_expression(alias, column_name, data_type):
    normalized_type = str(data_type or "").upper()
    ref = f"{alias}.{column_name}"

    if normalized_type == "DATE":
        return f"TO_DATE({ref})"

    if normalized_type.startswith("TIMESTAMP_NTZ"):
        return f"TO_TIMESTAMP_NTZ({ref})"

    if normalized_type.startswith("TIMESTAMP_TZ"):
        return f"TO_TIMESTAMP_TZ({ref})"

    if normalized_type.startswith("TIMESTAMP_LTZ"):
        return f"TO_TIMESTAMP_LTZ({ref})"

    if normalized_type == "TIME":
        return f"TO_TIME({ref})"

    return ref

# --------------------------------------------------
# GENERATE AND RUN MERGE SQL FOR SNOWFLAKE
# --------------------------------------------------
def snowflake_merge_raw_to_target(conn, database, schema, table, primary_keys, columns):
    """
    Perform MERGE from RAW to TGT table.

    Flow:
    1. Prepare merge columns
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

        raw_db = f"{database}_RAW"
        tgt_db = f"{database}_TGT"

        tgt = f'{tgt_db}.{schema}.{table}'
        raw = f'{raw_db}.{schema}.{table}'

        target_columns = columns
        target_schema_rows = get_table_schema_snowflake(
            conn,
            database,
            schema,
            table,
            table_role="TGT"
        )
        target_type_map = {
            str(column_name): str(data_type)
            for column_name, data_type in target_schema_rows
        }

        update_cols = [col for col in target_columns if col not in primary_keys]
        update_set = ", ".join([f"t.{col}=r.{col}" for col in update_cols])

        insert_cols = ", ".join(target_columns)
        insert_vals = ", ".join([f"r.{col}" for col in target_columns])

        pk_condition = " AND ".join([f"t.{pk}=r.{pk}" for pk in primary_keys])

        casted_select_list = ", ".join([
            f"{_build_snowflake_cast_expression('src', col, target_type_map.get(col))} AS {col}"
            for col in target_columns
        ])
        partition_by = ", ".join(primary_keys)
        order_by = ", ".join(primary_keys)

        merge_sql = f"""
                    MERGE INTO {tgt} t
                    USING (
                        SELECT *
                        FROM (
                            SELECT casted.*,
                                ROW_NUMBER() OVER (
                                    PARTITION BY {partition_by}
                                    ORDER BY {order_by}
                                ) rn
                            FROM (
                                SELECT {casted_select_list}
                                FROM {raw} src
                            ) casted
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
                logger.error(f"❌ MERGE FAILED for {table}: {str(e)}")
                print(f"❌ MERGE FAILED for {table}: {str(e)}")
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
                    print(f"❌ Truncate failed for {table}: {str(e)}")

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
    1. Prepare merge columns
    2. Build SQL components
    3. Return full MERGE script
    """

    try:
        raw_db = f"{database}_raw.{schema}.{table}"
        tgt_db = f"{database}_tgt.{schema}.{table}"

        # Normalize primary keys
        if isinstance(primary_keys, str):
            primary_keys = [pk.strip() for pk in primary_keys.split(",")]

        pk_set = set(pk.lower() for pk in primary_keys)

        # Columns for update
        update_cols = [c for c in columns if c.lower() not in pk_set]
        update_set = ", ".join([f"t.{c}=r.{c}" for c in update_cols])

        insert_cols = ", ".join(columns)
        insert_vals = ", ".join([f"r.{c}" for c in columns])

        pk_condition = " AND ".join([f"t.{pk}=r.{pk}" for pk in primary_keys])
        partition_by = ", ".join(primary_keys)
        order_by = ", ".join(primary_keys)

        merge_sql = f"""
        MERGE INTO {tgt_db} t
        USING (
            SELECT *
            FROM (
                SELECT *,
                       ROW_NUMBER() OVER (
                           PARTITION BY {partition_by}
                           ORDER BY {order_by}
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
        query = f"""
                TRUNCATE TABLE {database}_RAW.{schema}.{table};
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
    Retrieves columns from RAW table.
    """
    try:
        query = f"""
            SELECT column_name
            FROM `{project}.{dataset}.INFORMATION_SCHEMA.COLUMNS`
            WHERE table_name = '{table}'
            ORDER BY ordinal_position
        """

        query_job = client.query(query)
        cols = [row.column_name for row in query_job]

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
        update_set = ",\n        ".join([f"t.{c} = s.{c}" for c in update_cols])
        insert_names = ", ".join(columns)
        insert_values = ", ".join([f"s.{c}" for c in columns])
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


