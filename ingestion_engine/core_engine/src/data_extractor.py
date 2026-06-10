import os
import re
from datetime import datetime
from datetime import time as datetime_time

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from src.pipeline_logger import get_logger

logger = get_logger()


def _quote_sqlserver_identifier(identifier):
    return f"[{str(identifier).replace(']', ']]')}]"


def _format_sql_literal(value):
    if value is None or pd.isna(value):
        return "NULL"
    if isinstance(value, pd.Timestamp):
        value = value.to_pydatetime()
    if isinstance(value, datetime):
        return "CONVERT(datetime2, '" + value.strftime("%Y-%m-%d %H:%M:%S.%f") + "', 121)"
    if isinstance(value, str) and re.match(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}", value):
        return "CONVERT(datetime2, '" + value.replace("'", "''") + "', 121)"
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return str(value)
    return "'" + str(value).replace("'", "''") + "'"


def _normalize_column_lookup(df):
    return {str(col).strip().lower(): col for col in df.columns}


def _literal_series(value, row_count):
    text = str(value).strip()
    lowered = text.lower()

    # Explicit prefix markers
    if lowered in {"timestamp:now", "datetime:now", "now()"}:
        return pd.Series([pd.Timestamp.utcnow().tz_localize(None)] * row_count)
    if lowered.startswith("literal:"):
        return pd.Series([text.split(":", 1)[1]] * row_count)
    if lowered.startswith("int:"):
        return pd.Series([int(text.split(":", 1)[1])] * row_count)
    if lowered.startswith("float:"):
        return pd.Series([float(text.split(":", 1)[1])] * row_count)
    if lowered.startswith("bool:"):
        return pd.Series([text.split(":", 1)[1].strip().lower() == "true"] * row_count)

    # Auto-detect timestamp strings: YYYY-MM-DD HH:MM:SS[.ffffff]
    import re as _re
    if _re.match(r"^\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2}", text):
        try:
            return pd.Series([pd.Timestamp(text)] * row_count)
        except Exception:
            pass

    # Auto-detect date strings: YYYY-MM-DD
    if _re.match(r"^\d{4}-\d{2}-\d{2}$", text):
        try:
            return pd.Series([pd.Timestamp(text)] * row_count)
        except Exception:
            pass

    # Auto-detect plain booleans
    if lowered in {"true", "false"}:
        return pd.Series([lowered == "true"] * row_count)

    # Auto-detect plain integers
    if _re.match(r"^-?[0-9]+$", text):
        try:
            return pd.Series([int(text)] * row_count)
        except Exception:
            pass

    # Auto-detect plain floats
    if _re.match(r"^-?[0-9]+\.[0-9]*([eE][+-]?[0-9]+)?$", text):
        try:
            return pd.Series([float(text)] * row_count)
        except Exception:
            pass

    # Default: raw string pass-through
    return pd.Series([text] * row_count)


def query_execution(connection, source, query):
    """
    Execute a query on the source system and normalize datetime precision.
    Supports: sapsqlserver, mysql, oracle, teradata
    """
    try:
        if source not in ("sapsqlserver", "sqlserver", "mysql", "postgres", "oracle", "teradata"):
            logger.info(f"Unsupported source type: {source}")
            raise ValueError(f"Unsupported source type: {source}")

        df = pd.read_sql(query, connection, coerce_float=True).copy()

        for col in df.columns:
            if str(df[col].dtype).startswith("datetime64"):
                df[col] = df[col].astype("datetime64[us]")

        return df

    except pd.errors.DatabaseError as e:
        logger.info(f"Database error during query execution: {str(e)}")
        raise Exception(f"Database error during query execution: {str(e)}")
    except Exception as e:
        logger.info(f"Query execution failed: {str(e)}")
        raise Exception(f"Query execution failed: {str(e)}")


def build_mapped_dataframe(df, target_columns, mapped_columns):
    """
    Build a target-shaped DataFrame from selected source data and mapping JSON.

    Mapping values:
    - source column name: copy source data into the target column
    - NULL: create a null-valued column
    - DEFAULT: omit the column so loader/table defaults can apply where supported
    - literal:/int:/float:/bool:/timestamp:now: create a constant column
    """
    output = pd.DataFrame(index=df.index)
    source_lookup = _normalize_column_lookup(df)

    for target_column in target_columns:
        expression = mapped_columns.get(target_column, target_column)
        token = str(expression).strip()
        upper_token = token.upper()

        if upper_token == "DEFAULT":
            logger.info(f"Column '{target_column}' marked DEFAULT; omitting from parquet")
            continue

        if upper_token in {"NULL", "NONE"}:
            output[target_column] = pd.NA
            continue

        source_column = source_lookup.get(token.lower())
        if source_column is not None:
            output[target_column] = df[source_column]
            continue

        if ":" in token or token.lower() in {"now()", "timestamp:now", "datetime:now"}:
            output[target_column] = _literal_series(token, len(df)).values
            continue

        raise ValueError(
            f"Mapping for target column '{target_column}' references missing source column "
            f"or unsupported expression: {expression}"
        )

    return output


def write_dataframe_to_parquet(df, local_folder_path, table, stringify_datetime=False):
    os.makedirs(local_folder_path, exist_ok=True)

    safe_table = table.replace("/", "_")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    parquet_file = f"{safe_table}_{timestamp}.parquet"
    parquet_file_path = os.path.join(local_folder_path, parquet_file)

    logger.info("Schema retrieved")
    logger.info(df.dtypes)

    df = df.copy()
    for col in df.columns:
        dtype = str(df[col].dtype)
        if str(df[col].dtype).startswith("datetime64"):
            if stringify_datetime:
                df[col] = df[col].dt.strftime("%Y-%m-%d %H:%M:%S.%f")
            continue
        if dtype == "object":
            non_null = df[col].dropna()
            if non_null.empty:
                continue
            if non_null.map(lambda value: isinstance(value, datetime_time)).any():
                df[col] = df[col].map(lambda value: value.isoformat() if isinstance(value, datetime_time) else value)
            elif non_null.map(lambda value: isinstance(value, (bytes, bytearray))).any():
                df[col] = df[col].map(lambda value: value.hex() if isinstance(value, (bytes, bytearray)) else value)
            else:
                df[col] = df[col].where(df[col].isna(), df[col].astype(str))

    table_arrow = pa.Table.from_pandas(df, preserve_index=False)
    pq.write_table(table_arrow, parquet_file_path, compression="snappy")

    parquet_count = pq.ParquetFile(parquet_file_path).metadata.num_rows
    if len(df) != parquet_count:
        raise Exception(f"Reconciliation failed: Source={len(df)} Parquet={parquet_count}")

    logger.info("Reconciliation Passed")
    logger.info(f"Parquet file created at {parquet_file_path}")
    return parquet_file_path


def extract_sapsqlserver_data(conn, local_folder_path, database, schema, table):
    logger.info(f"Starting extraction for {database}.{schema}.{table}")

    try:
        query = f"SELECT * FROM [{database}].[{schema}].[{table}]"
        df = query_execution(conn, "sapsqlserver", query)
        parquet_file_path = write_dataframe_to_parquet(df, local_folder_path, table)
        logger.info(f"Extraction completed for {table}")
        return parquet_file_path
    except FileNotFoundError:
        logger.info(f"Invalid folder path: {local_folder_path}")
        raise FileNotFoundError(f"Invalid folder path: {local_folder_path}")
    except PermissionError as e:
        logger.info(f"Permission error while writing file: {str(e)}")
        raise Exception(f"Permission error while writing file: {str(e)}")
    except pd.errors.DatabaseError as e:
        logger.info(f"Database query failed: {str(e)}")
        raise Exception(f"Database query failed: {str(e)}")
    except pa.ArrowInvalid as e:
        logger.info(f"PyArrow conversion failed: {str(e)}")
        raise Exception(f"PyArrow conversion failed: {str(e)}")
    except Exception as e:
        logger.info(f"Error during data extraction: {str(e)}")
        raise Exception(f"Error during data extraction: {str(e)}")


def extract_sapsqlserver_incremental_data(
    conn,
    local_folder_path,
    table_metadata,
    last_watermark_value=None,
    target_system=None
):
    logger.info(
        "Starting incremental extraction for "
        f"{table_metadata.source_database}.{table_metadata.source_schema}.{table_metadata.source_table}"
    )

    try:
        selected_columns = list(dict.fromkeys(table_metadata.source_columns))
        column_sql = ", ".join(_quote_sqlserver_identifier(col) for col in selected_columns)
        table_sql = ".".join([
            _quote_sqlserver_identifier(table_metadata.source_database),
            _quote_sqlserver_identifier(table_metadata.source_schema),
            _quote_sqlserver_identifier(table_metadata.source_table),
        ])

        query = f"SELECT {column_sql} FROM {table_sql}"
        if last_watermark_value is not None and not pd.isna(last_watermark_value):
            watermark_col = _quote_sqlserver_identifier(table_metadata.watermark_column)
            query += f" WHERE {watermark_col} > {_format_sql_literal(last_watermark_value)}"
        query += f" ORDER BY {_quote_sqlserver_identifier(table_metadata.watermark_column)}"

        logger.info(f"Incremental extract query: {query}")
        source_df = query_execution(conn, "sapsqlserver", query)
        mapped_df = build_mapped_dataframe(
            source_df,
            table_metadata.target_columns,
            table_metadata.mapped_columns
        )

        parquet_file_path = write_dataframe_to_parquet(
            mapped_df,
            local_folder_path,
            table_metadata.source_table,
            stringify_datetime=str(target_system).lower() == "snowflake"
        )

        extracted_rows = len(mapped_df)
        max_batch_watermark = last_watermark_value
        if extracted_rows > 0:
            # Determine the actual max watermark in this batch
            wm_col = table_metadata.watermark_column.lower()
            col_lookup = {c.lower(): c for c in source_df.columns}
            actual_col = col_lookup.get(wm_col, table_metadata.watermark_column)
            batch_max = source_df[actual_col].max()
            if pd.notna(batch_max):
                max_batch_watermark = batch_max

        logger.info(
            f"Incremental extraction completed for {table_metadata.source_table}; "
            f"rows={extracted_rows}"
        )
        return parquet_file_path, max_batch_watermark

    except Exception as e:
        logger.info(f"Error during incremental data extraction: {str(e)}")
        raise Exception(f"Error during incremental data extraction: {str(e)}")


def _quote_mysql_identifier(identifier):
    return f"`{str(identifier).replace('`', '``')}`"


def _format_mysql_literal(value):
    if value is None or pd.isna(value):
        return "NULL"
    if isinstance(value, pd.Timestamp):
        value = value.to_pydatetime()
    if isinstance(value, datetime):
        return "'" + value.strftime("%Y-%m-%d %H:%M:%S") + "'"
    if isinstance(value, str) and re.match(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}", value):
        return "'" + value.replace("'", "''") + "'"
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return str(value)
    return "'" + str(value).replace("'", "''") + "'"


def extract_mysql_incremental_data(
    conn,
    local_folder_path,
    table_metadata,
    last_watermark_value=None,
    target_system=None
):
    logger.info(
        "Starting MySQL incremental extraction for "
        f"{table_metadata.source_database}.{table_metadata.source_schema}.{table_metadata.source_table}"
    )

    try:
        selected_columns = list(dict.fromkeys(table_metadata.source_columns))
        column_sql = ", ".join(_quote_mysql_identifier(col) for col in selected_columns)
        table_sql = f"{_quote_mysql_identifier(table_metadata.source_schema)}.{_quote_mysql_identifier(table_metadata.source_table)}"

        query = f"SELECT {column_sql} FROM {table_sql}"
        if last_watermark_value is not None and not pd.isna(last_watermark_value):
            watermark_col = _quote_mysql_identifier(table_metadata.watermark_column)
            query += f" WHERE {watermark_col} > {_format_mysql_literal(last_watermark_value)}"
        query += f" ORDER BY {_quote_mysql_identifier(table_metadata.watermark_column)}"

        logger.info(f"MySQL incremental extract query: {query}")
        source_df = query_execution(conn, "mysql", query)
        mapped_df = build_mapped_dataframe(
            source_df,
            table_metadata.target_columns,
            table_metadata.mapped_columns
        )

        parquet_file_path = write_dataframe_to_parquet(
            mapped_df,
            local_folder_path,
            table_metadata.source_table,
            stringify_datetime=str(target_system).lower() == "snowflake"
        )

        extracted_rows = len(mapped_df)
        max_batch_watermark = last_watermark_value
        if extracted_rows > 0:
            wm_col = table_metadata.watermark_column.lower()
            col_lookup = {c.lower(): c for c in source_df.columns}
            actual_col = col_lookup.get(wm_col, table_metadata.watermark_column)
            batch_max = source_df[actual_col].max()
            if pd.notna(batch_max):
                max_batch_watermark = batch_max

        logger.info(f"MySQL incremental extraction completed for {table_metadata.source_table}; rows={extracted_rows}")
        return parquet_file_path, max_batch_watermark

    except Exception as e:
        logger.info(f"Error during MySQL incremental extraction: {str(e)}")
        raise Exception(f"Error during MySQL incremental extraction: {str(e)}")


def _quote_oracle_identifier(identifier):
    return f'"{str(identifier).upper()}"'


def _format_oracle_literal(value):
    if value is None or pd.isna(value):
        return "NULL"
    if isinstance(value, pd.Timestamp):
        value = value.to_pydatetime()
    if isinstance(value, datetime):
        return "TO_TIMESTAMP('" + value.strftime("%Y-%m-%d %H:%M:%S") + "', 'YYYY-MM-DD HH24:MI:SS')"
    if isinstance(value, str) and re.match(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}", value):
        return "TO_TIMESTAMP('" + value.replace("'", "''") + "', 'YYYY-MM-DD HH24:MI:SS')"
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return str(value)
    return "'" + str(value).replace("'", "''") + "'"


def extract_oracle_incremental_data(
    conn,
    local_folder_path,
    table_metadata,
    last_watermark_value=None,
    target_system=None
):
    logger.info(
        "Starting Oracle incremental extraction for "
        f"{table_metadata.source_schema}.{table_metadata.source_table}"
    )

    try:
        selected_columns = list(dict.fromkeys(table_metadata.source_columns))
        column_sql = ", ".join(_quote_oracle_identifier(col) for col in selected_columns)
        table_sql = f"{_quote_oracle_identifier(table_metadata.source_schema)}.{_quote_oracle_identifier(table_metadata.source_table)}"

        query = f"SELECT {column_sql} FROM {table_sql}"
        if last_watermark_value is not None and not pd.isna(last_watermark_value):
            watermark_col = _quote_oracle_identifier(table_metadata.watermark_column)
            query += f" WHERE {watermark_col} > {_format_oracle_literal(last_watermark_value)}"
        query += f" ORDER BY {_quote_oracle_identifier(table_metadata.watermark_column)}"

        logger.info(f"Oracle incremental extract query: {query}")
        source_df = query_execution(conn, "oracle", query)
        mapped_df = build_mapped_dataframe(
            source_df,
            table_metadata.target_columns,
            table_metadata.mapped_columns
        )

        parquet_file_path = write_dataframe_to_parquet(
            mapped_df,
            local_folder_path,
            table_metadata.source_table,
            stringify_datetime=str(target_system).lower() == "snowflake"
        )

        extracted_rows = len(mapped_df)
        max_batch_watermark = last_watermark_value
        if extracted_rows > 0:
            wm_col = table_metadata.watermark_column.upper()
            # Oracle returns column names in uppercase
            col_lookup = {c.upper(): c for c in source_df.columns}
            actual_col = col_lookup.get(wm_col, table_metadata.watermark_column)
            batch_max = source_df[actual_col].max()
            if pd.notna(batch_max):
                max_batch_watermark = batch_max

        logger.info(f"Oracle incremental extraction completed for {table_metadata.source_table}; rows={extracted_rows}")
        return parquet_file_path, max_batch_watermark

    except Exception as e:
        logger.info(f"Error during Oracle incremental extraction: {str(e)}")
        raise Exception(f"Error during Oracle incremental extraction: {str(e)}")


def extract_teradata_incremental_data(
    conn,
    local_folder_path,
    table_metadata,
    last_watermark_value=None,
    target_system=None
):
    logger.info(
        "Starting Teradata incremental extraction for "
        f"{table_metadata.source_database}.{table_metadata.source_table}"
    )

    try:
        selected_columns = list(dict.fromkeys(table_metadata.source_columns))
        column_sql = ", ".join(f'"{col}"' for col in selected_columns)
        if table_metadata.source_database:
            table_sql = f'"{table_metadata.source_database}"."{table_metadata.source_table}"'
        else:
            table_sql = f'"{table_metadata.source_table}"'

        query = f"SELECT {column_sql} FROM {table_sql}"
        if last_watermark_value is not None and not pd.isna(last_watermark_value):
            watermark_col = f'"{table_metadata.watermark_column}"'
            def _lit(v):
                if v is None or pd.isna(v): return "NULL"
                if isinstance(v, pd.Timestamp): v = v.to_pydatetime()
                import datetime as _dt
                if isinstance(v, _dt.datetime): return "TIMESTAMP '" + v.strftime("%Y-%m-%d %H:%M:%S") + "'"
                if isinstance(v, (int, float)) and not isinstance(v, bool): return str(v)
                return "'" + str(v).replace("'", "''") + "'"
            query += f" WHERE {watermark_col} > {_lit(last_watermark_value)}"
        query += f" ORDER BY \"{table_metadata.watermark_column}\""

        logger.info(f"Teradata incremental extract query: {query}")
        source_df = query_execution(conn, "teradata", query)
        mapped_df = build_mapped_dataframe(
            source_df,
            table_metadata.target_columns,
            table_metadata.mapped_columns
        )

        parquet_file_path = write_dataframe_to_parquet(
            mapped_df,
            local_folder_path,
            table_metadata.source_table,
            stringify_datetime=str(target_system).lower() == "snowflake"
        )

        extracted_rows = len(mapped_df)
        max_batch_watermark = last_watermark_value
        if extracted_rows > 0:
            wm_col = table_metadata.watermark_column.lower()
            col_lookup = {c.lower(): c for c in source_df.columns}
            actual_col = col_lookup.get(wm_col, table_metadata.watermark_column)
            batch_max = source_df[actual_col].max()
            if pd.notna(batch_max):
                max_batch_watermark = batch_max

        logger.info(f"Teradata incremental extraction completed for {table_metadata.source_table}; rows={extracted_rows}")
        return parquet_file_path, max_batch_watermark

    except Exception as e:
        logger.info(f"Error during Teradata incremental extraction: {str(e)}")
        raise Exception(f"Error during Teradata incremental extraction: {str(e)}")


# ─────────────────────────────────────────────────────────────────────────────
# Full Load Specific Helper Functions and Data Extraction
# ─────────────────────────────────────────────────────────────────────────────

DATE_SOURCE_TYPES = {"date"}
DATETIME_SOURCE_TYPES = {
    "datetime",
    "datetime2",
    "smalldatetime",
    "datetimeoffset",
    "timestamp",
    "timestamp without time zone",
    "timestamp with time zone",
    "timestamp with local time zone",
}
TIME_SOURCE_TYPES = {"time"}


def build_source_table_reference(source: str, database: str, schema: str, table: str) -> str:
    if source in {"sapsqlserver", "sqlserver"}:
        return f"[{database}].[{schema}].[{table}]"

    if source == "mysql":
        return f"`{schema}`.`{table}`"

    if source == "postgres":
        return f'"{schema}"."{table}"'

    if source == "oracle":
        return f'"{schema.upper()}"."{table.upper()}"'

    raise ValueError(f"Unsupported source type: {source}")


def build_source_columns_query(source: str, database: str, schema: str, table: str) -> str:
    if source in {"sapsqlserver", "sqlserver"}:
        return f"""
        SELECT COLUMN_NAME, DATA_TYPE
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_CATALOG = '{database}'
          AND TABLE_SCHEMA = '{schema}'
          AND TABLE_NAME = '{table}'
        """

    if source == "mysql":
        return f"""
        SELECT COLUMN_NAME, DATA_TYPE
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = '{schema}'
          AND TABLE_NAME = '{table}'
        ORDER BY ORDINAL_POSITION
        """

    if source == "postgres":
        return f"""
        SELECT COLUMN_NAME, DATA_TYPE
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_CATALOG = '{database}'
          AND TABLE_SCHEMA = '{schema}'
          AND TABLE_NAME = '{table}'
        ORDER BY ORDINAL_POSITION
        """

    if source == "oracle":
        return f"""
        SELECT COLUMN_NAME, DATA_TYPE
        FROM ALL_TAB_COLUMNS
        WHERE OWNER = '{schema.upper()}'
          AND TABLE_NAME = '{table.upper()}'
        ORDER BY COLUMN_ID
        """

    raise ValueError(f"Unsupported source type: {source}")


def _build_arrow_table(
    df: pd.DataFrame,
    source_types: dict[str, str] | None = None
) -> pa.Table:
    arrays = []
    names = []

    for col in df.columns:
        source_type = (source_types or {}).get(col, "").strip().lower()
        series = df[col]
        lower_col = col.lower()

        if source_type in DATE_SOURCE_TYPES or _is_date_like_column(lower_col, source_type):
            parsed = _coerce_datetime(series)
            values = [
                value.date() if not pd.isna(value) else None
                for value in parsed
            ]
            arrays.append(pa.array(values, type=pa.date32()))
        elif source_type in DATETIME_SOURCE_TYPES or _is_datetime_like_column(lower_col, source_type):
            parsed = _coerce_datetime(series)
            values = [
                value.to_pydatetime() if not pd.isna(value) else None
                for value in parsed
            ]
            arrays.append(pa.array(values, type=pa.timestamp("us")))
        else:
            arrays.append(pa.array(series, from_pandas=True))

        names.append(col)

    return pa.Table.from_arrays(arrays, names=names)


def _coerce_datetime(series: pd.Series) -> pd.Series:
    return pd.to_datetime(series, errors="coerce")


def _is_date_like_column(column_name: str, source_type: str) -> bool:
    if source_type in DATE_SOURCE_TYPES:
        return True
    if source_type:
        return False

    return (
        column_name.endswith("date")
        or column_name in {"dob", "dateofbirth", "birthdate"}
        or column_name.endswith("_dt")
    )


def _is_datetime_like_column(column_name: str, source_type: str) -> bool:
    if source_type in DATETIME_SOURCE_TYPES:
        return True
    if source_type:
        return False

    return (
        "timestamp" in column_name
        or column_name.endswith("datetime")
        or column_name in {
            "createdat",
            "updatedat",
            "modifiedat",
            "lastmodifiedat",
            "insertedat",
            "deletedat",
        }
    )


def _is_time_like_column(column_name: str, source_type: str) -> bool:
    if source_type in TIME_SOURCE_TYPES:
        return True
    if source_type:
        return False

    return "time" in column_name and not column_name.endswith("date")


def _stringify_object_series(series: pd.Series) -> pd.Series:
    return series.map(lambda value: None if pd.isna(value) else str(value))


def normalize_dataframe_for_parquet(
    df: pd.DataFrame,
    source_types: dict[str, str] | None = None,
    temporal_mode: str = "native"
) -> pd.DataFrame:
    normalized_df = df.copy()

    for col in normalized_df.columns:
        dtype = str(normalized_df[col].dtype)
        lower_col = col.lower()
        source_type = (source_types or {}).get(col, "").strip().lower()

        if source_type in DATE_SOURCE_TYPES or _is_date_like_column(lower_col, source_type):
            parsed_date = _coerce_datetime(normalized_df[col])
            if temporal_mode == "snowflake_text":
                normalized_df[col] = parsed_date.dt.strftime("%Y-%m-%d").where(
                    parsed_date.notna(),
                    None
                )
            else:
                normalized_df[col] = parsed_date.dt.date.where(
                    parsed_date.notna(),
                    None
                )
            continue

        if str(normalized_df[col].dtype).startswith("datetime64"):
            normalized_df[col] = normalized_df[col].astype("datetime64[us]")
            continue

        if source_type in DATETIME_SOURCE_TYPES or _is_datetime_like_column(lower_col, source_type):
            parsed_datetime = _coerce_datetime(normalized_df[col])
            if temporal_mode == "snowflake_text":
                normalized_df[col] = parsed_datetime.dt.strftime("%Y-%m-%d %H:%M:%S.%f").where(
                    parsed_datetime.notna(),
                    None
                )
            else:
                normalized_df[col] = parsed_datetime.astype("datetime64[us]")
            continue

        if _is_time_like_column(lower_col, source_type):
            parsed_time = _coerce_datetime(normalized_df[col])

            if parsed_time.notna().any():
                normalized_df[col] = parsed_time.dt.strftime("%H:%M:%S").where(
                    parsed_time.notna(),
                    None
                )
            else:
                normalized_df[col] = _stringify_object_series(normalized_df[col])
            continue

        if "timestamp" in lower_col:
            parsed_datetime = _coerce_datetime(normalized_df[col])
            normalized_df[col] = parsed_datetime.astype("datetime64[us]")
            continue

        if dtype == "object":
            normalized_df[col] = _stringify_object_series(normalized_df[col])

    return normalized_df


def extract_source_data(conn, source, local_folder_path, database, schema, table, target_system=None):
    logger.info(f"Starting extraction for {database}.{schema}.{table}")

    try:
        # Ensure local directory exists
        os.makedirs(local_folder_path, exist_ok=True)

        # Build query dynamically
        query = f"SELECT * FROM {build_source_table_reference(source, database, schema, table)}"

        # Fetch data
        df = query_execution(conn, source, query)

        # Read source datatypes so parquet uses the same logical date/timestamp types.
        schema_query = build_source_columns_query(source, database, schema, table)
        schema_df = pd.read_sql(schema_query, conn)
        source_types = {
            str(row["COLUMN_NAME"]): str(row["DATA_TYPE"])
            for _, row in schema_df.iterrows()
        }
        source_types["__target_system__"] = str(target_system or "").strip().lower()

        # Handle invalid characters in table name for file naming
        safe_table = table.replace("/", "_")

        # Generate timestamp-based file name
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        parquet_file = f"{safe_table}_{timestamp}.parquet"
        parquet_file_path = os.path.join(local_folder_path, parquet_file)

        # Log schema details
        logger.info("Schema retrieved")
        logger.info(df.dtypes)

        temporal_mode = "native"
        if str(source_types.get("__target_system__", "")).strip().lower() == "snowflake":
            temporal_mode = "snowflake_text"

        source_types = {
            key: value
            for key, value in source_types.items()
            if key != "__target_system__"
        }

        df = normalize_dataframe_for_parquet(df, source_types, temporal_mode=temporal_mode)

        # Convert pandas DataFrame to Arrow Table
        if temporal_mode == "snowflake_text":
            table_arrow = pa.Table.from_pandas(df, preserve_index=False)
        else:
            table_arrow = _build_arrow_table(df, source_types)

        # Write Parquet file with compression
        pq.write_table(
            table_arrow,
            parquet_file_path,
            compression="snappy"
        )

        # ---------- RECONCILIATION ----------
        # Read back Parquet to validate row count
        parquet_df = pq.read_table(parquet_file_path).to_pandas()

        source_count = len(df)
        parquet_count = len(parquet_df)

        logger.info(f"Source count: {source_count}")
        logger.info(f"Parquet count: {parquet_count}")

        # Validate counts match
        if source_count != parquet_count:
            raise Exception(
                f"Reconciliation failed: Source={source_count} Parquet={parquet_count}"
            )

        logger.info("Reconciliation Passed")
        logger.info(f"Parquet file created at {parquet_file_path}")
        logger.info(f"Extraction completed for {table}")

        return parquet_file_path

    except FileNotFoundError:
        # Invalid directory path
        logger.info(f"Invalid folder path: {local_folder_path}")
        raise FileNotFoundError(f"Invalid folder path: {local_folder_path}")

    except PermissionError as e:
        # File system permission issues
        logger.info(f"Permission error while writing file: {str(e)}")
        raise Exception(f"Permission error while writing file: {str(e)}")

    except pd.errors.DatabaseError as e:
        # SQL Server read issues
        logger.info(f"Database query failed: {str(e)}")
        raise Exception(f"Database query failed: {str(e)}")

    except pa.ArrowInvalid as e:
        # Arrow conversion issues
        logger.info(f"PyArrow conversion failed: {str(e)}")
        raise Exception(f"PyArrow conversion failed: {str(e)}")

    except Exception as e:
        # Catch-all for unexpected failures
        logger.info(f"Error during data extraction: {str(e)}")
        raise Exception(f"Error during data extraction: {str(e)}")
