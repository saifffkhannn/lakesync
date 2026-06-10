import pandas as pd
import os
import pyarrow as pa
import pyarrow.parquet as pq
from datetime import datetime
from src.custom_logger import get_logger

logger = get_logger()

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
    """
    Build a PyArrow table while preserving source date/datetime intent.

    Snowflake COPY from Parquet is sensitive to the physical Parquet type.
    In particular, SQL Server DATE values must be written as Parquet DATE
    rather than timestamp values, otherwise COPY may fail while coercing
    microsecond epoch values into DATE columns.
    """

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
    """
    Normalize dataframe values before writing parquet.

    Date-like object columns are converted to datetime when possible so the
    target system receives proper timestamp values instead of free-form strings.
    """

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


def query_execution(connection, source, query):
    """
    Executes a query on the specified source system.

    Flow:
    1. Validate source type
    2. Execute query using pandas
    3. Normalize datetime columns
    4. Return DataFrame
    """

    try:
        if source in {"sapsqlserver", "sqlserver", "mysql", "postgres", "oracle"}:

            # Execute query and load into DataFrame
            df = pd.read_sql(
                query,
                connection,
                coerce_float=True
            )

            # Create a copy to avoid modifying original reference
            df = df.copy()

            # Normalize datetime precision to microseconds
            for col in df.columns:
                if str(df[col].dtype).startswith("datetime64"):
                    df[col] = df[col].astype("datetime64[us]")

            return df

        else:
            logger.info(f"Unsupported source type: {source}")
            raise ValueError(f"Unsupported source type: {source}")

    except pd.errors.DatabaseError as e:
        # Database-level issues (query syntax, permissions, etc.)
        logger.info(f"Database error during query execution: {str(e)}")
        raise Exception(f"Database error during query execution: {str(e)}")

    except Exception as e:
        # General failure
        logger.info(f"Query execution failed: {str(e)}")
        raise Exception(f"Query execution failed: {str(e)}")


def extract_source_data(conn, source, local_folder_path, database, schema, table, target_system=None):
    """
    Extracts data from SQL Server and saves it as Parquet.

    Flow:
    1. Create local directory
    2. Execute SELECT query
    3. Apply schema fixes
    4. Write to Parquet
    5. Perform reconciliation check
    """

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


def extract_sapsqlserver_data(conn, local_folder_path, database, schema, table, target_system=None):
    return extract_source_data(
        conn,
        "sapsqlserver",
        local_folder_path,
        database,
        schema,
        table,
        target_system
    )
