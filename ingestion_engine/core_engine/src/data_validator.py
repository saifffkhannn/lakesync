import pyarrow.parquet as pq
import pandas as pd
import re
 

def _quote_sqlserver_identifier(identifier):
    return f"[{str(identifier).replace(']', ']]')}]"


def _format_sql_literal(value):
    if value is None or pd.isna(value):
        return "NULL"
    if isinstance(value, pd.Timestamp):
        value = value.to_pydatetime()
    if hasattr(value, "strftime"):
        return "CONVERT(datetime2, '" + value.strftime("%Y-%m-%d %H:%M:%S.%f") + "', 121)"
    if isinstance(value, str) and re.match(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}", value):
        return "CONVERT(datetime2, '" + value.replace("'", "''") + "', 121)"
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return str(value)
    return "'" + str(value).replace("'", "''") + "'"

 
def get_source_row_count(conn, database, schema, table, source=None):
    """
    Fetch row count from source SQL Server table.
 
    Flow:
    1. Build COUNT(*) query*
    2. Execute using pandas
    3. Extract count from DataFrame
    """
 
    try:
        # Construct COUNT query
        query = f"SELECT COUNT(*) as row_count FROM [{database}].[{schema}].[{table}]"
 
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


def get_incremental_source_row_count(conn, table_metadata, last_watermark_value=None):
    """
    Count rows in the incremental source window.
    Supports: sapsqlserver, mysql, oracle
    """
    try:
        source = str(getattr(table_metadata, "source_system", "sapsqlserver")).lower()

        if source == "mysql":
            def _q(i): return f"`{str(i).replace('`', '``')}`"
            def _lit(v):
                if v is None or pd.isna(v): return "NULL"
                if isinstance(v, pd.Timestamp): v = v.to_pydatetime()
                import datetime as _dt
                if isinstance(v, _dt.datetime): return "'" + v.strftime("%Y-%m-%d %H:%M:%S") + "'"
                if isinstance(v, (int, float)) and not isinstance(v, bool): return str(v)
                return "'" + str(v).replace("'", "''") + "'"
            table_name = f"{_q(table_metadata.source_schema)}.{_q(table_metadata.source_table)}"
            query = f"SELECT COUNT(*) as row_count FROM {table_name}"
            if last_watermark_value is not None and not pd.isna(last_watermark_value):
                query += f" WHERE {_q(table_metadata.watermark_column)} > {_lit(last_watermark_value)}"

        elif source == "oracle":
            def _q(i): return f'"{str(i).upper()}"'
            def _lit(v):
                if v is None or pd.isna(v): return "NULL"
                if isinstance(v, pd.Timestamp): v = v.to_pydatetime()
                import datetime as _dt
                if isinstance(v, _dt.datetime): return "TO_TIMESTAMP('" + v.strftime("%Y-%m-%d %H:%M:%S") + "', 'YYYY-MM-DD HH24:MI:SS')"
                if isinstance(v, (int, float)) and not isinstance(v, bool): return str(v)
                return "'" + str(v).replace("'", "''") + "'"
            table_name = f"{_q(table_metadata.source_schema)}.{_q(table_metadata.source_table)}"
            query = f"SELECT COUNT(*) as row_count FROM {table_name}"
            if last_watermark_value is not None and not pd.isna(last_watermark_value):
                query += f" WHERE {_q(table_metadata.watermark_column)} > {_lit(last_watermark_value)}"

        elif source == "teradata":
            def _q(i): return f'"{str(i)}"'
            def _lit(v):
                if v is None or pd.isna(v): return "NULL"
                if isinstance(v, pd.Timestamp): v = v.to_pydatetime()
                import datetime as _dt
                if isinstance(v, _dt.datetime): return "TIMESTAMP '" + v.strftime("%Y-%m-%d %H:%M:%S") + "'"
                if isinstance(v, (int, float)) and not isinstance(v, bool): return str(v)
                return "'" + str(v).replace("'", "''") + "'"
            if table_metadata.source_database:
                table_name = f"{_q(table_metadata.source_database)}.{_q(table_metadata.source_table)}"
            else:
                table_name = _q(table_metadata.source_table)
            query = f"SELECT COUNT(*) as row_count FROM {table_name}"
            if last_watermark_value is not None and not pd.isna(last_watermark_value):
                query += f" WHERE {_q(table_metadata.watermark_column)} > {_lit(last_watermark_value)}"

        else:
            # Default: sapsqlserver with T-SQL quoting
            table_name = ".".join([
                _quote_sqlserver_identifier(table_metadata.source_database),
                _quote_sqlserver_identifier(table_metadata.source_schema),
                _quote_sqlserver_identifier(table_metadata.source_table),
            ])
            query = f"SELECT COUNT(*) as row_count FROM {table_name}"
            if last_watermark_value is not None and not pd.isna(last_watermark_value):
                query += (
                    f" WHERE {_quote_sqlserver_identifier(table_metadata.watermark_column)} "
                    f"> {_format_sql_literal(last_watermark_value)}"
                )

        df = pd.read_sql(query, conn)
        return int(df.iloc[0]["row_count"])
    except Exception as e:
        raise Exception(f"Error fetching incremental source row count: {str(e)}")

 
 
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
    try:
        safe_table = table.replace("/", "_")

        if target == "bigquery":
            safe_table = safe_table.lower()
            tgt_catalog = catalog.lower()
            query = f"SELECT COUNT(*) as row_count FROM `{conn.project}.{tgt_catalog}.{safe_table}`"
            result = conn.query(query).result()
            return list(result)[0]["row_count"]
        else:
            # Use exact database name — no _TGT suffix for any target
            db_name = catalog
            query = f"SELECT COUNT(*) FROM {db_name}.{schema}.{safe_table}"
            cursor = conn.cursor()
            try:
                cursor.execute(query)
                return cursor.fetchone()[0]
            finally:
                try:
                    cursor.close()
                except Exception:
                    pass
    except Exception as e:
        raise Exception(f"Error fetching target row count: {str(e)}")
