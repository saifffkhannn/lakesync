import pyarrow.parquet as pq
import pandas as pd
 
 
def get_source_row_count(conn, database, schema, table, source="sapsqlserver"):
    """
    Fetch row count from source SQL Server table.
 
    Flow:
    1. Build COUNT(*) query*
    2. Execute using pandas
    3. Extract count from DataFrame
    """
 
    try:
        # Construct COUNT query
        if source in {"sapsqlserver", "sqlserver"}:
            query = f"SELECT COUNT(*) as row_count FROM [{database}].[{schema}].[{table}]"
        elif source == "mysql":
            query = f"SELECT COUNT(*) as row_count FROM `{schema}`.`{table}`"
        elif source == "postgres":
            query = f'SELECT COUNT(*) as row_count FROM "{schema}"."{table}"'
        elif source == "oracle":
            query = f'SELECT COUNT(*) as row_count FROM "{schema.upper()}"."{table.upper()}"'
        else:
            raise ValueError(f"Unsupported source type: {source}")
 
        # Execute query
        df = pd.read_sql(query, conn)
 
        # Return row count as integer
        return int(df.iloc[0]["row_count"])
 
    except pd.errors.DatabaseError as e:
        # Database-related issues (query failure, permissions, etc.)
        raise Exception(f"Source row count query failed: {str(e)}")
 
    except Exception as e:
        # General failure
        raise Exception(f"Error fetching source row count: {str(e)}")
 
 
def get_parquet_row_count(parquet_path):
    """
    Fetch row count from Parquet file.
 
    Flow:
    1. Open Parquet file
    2. Read metadata
    3. Return total row count
    """
 
    try:
        # Load Parquet file metadata
        parquet_file = pq.ParquetFile(parquet_path)
 
        # Return number of rows from metadata
        return parquet_file.metadata.num_rows
 
    except FileNotFoundError as e:
        # File path issues
        raise Exception(f"Parquet file not found: {str(e)}")
 
    except Exception as e:
        # General failure
        raise Exception(f"Error reading parquet row count: {str(e)}")
 
 
def get_target_row_count(conn, catalog, schema, table, target=None):
    """
    Fetch row count from target system.
 
    Supports:
    - BigQuery
    - Databricks / Snowflake (generic SQL)
 
    Flow:
    1. Build target-specific query
    2. Execute query
    3. Return row count
    """
 
    try:
        # Construct catalog names
        raw_catalog = f"{catalog}_raw"
        tgt_catalog = f"{catalog}_tgt".lower()
 
        # Handle special characters in table name
        safe_table = table.replace("/", "_")
 
        # BigQuery handling
        if target == "bigquery":
            safe_table = safe_table.lower()
 
            query = f"""
            SELECT COUNT(*) as row_count
            FROM `{conn.project}.{tgt_catalog}.{safe_table}`
            """
 
            result = conn.query(query).result()
            return list(result)[0]["row_count"]
 
        else:
            # Generic SQL execution (Databricks / Snowflake)
            query = f"SELECT COUNT(*) FROM {tgt_catalog}.{schema}.{safe_table}"
 
            cursor = conn.cursor()
            try:
                cursor.execute(query)
                return cursor.fetchone()[0]
            finally:
                # Ensure cursor is always closed
                try:
                    cursor.close()
                except Exception:
                    pass
 
    except Exception as e:
        # Catch-all for all failures
        raise Exception(f"Error fetching target row count: {str(e)}")
