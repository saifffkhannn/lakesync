import pandas as pd
from google.cloud import bigquery
from src.pipeline_logger import get_logger
from src.config_parser import parse_config
from src.db_connections import get_snowflake_stage_schema
from src.data_extractor import build_source_columns_query
from src.database_helpers import get_raw_db, get_target_db

logger = get_logger()


def _create_snowflake_stage(target_conn, config_path, cloud, database):
    if cloud.lower() in ("local", "none", ""):
        return
    config = parse_config(config_path)
    stage_schema = "cloud_stage"
    target_db = get_target_db(database)
    stage_full_name = f"{target_db}.{stage_schema}.stagename"

    if cloud.lower() == "aws":
        aws_cfg = config["aws"]
        key_id = aws_cfg["aws_access_key_id"].strip()
        secret = aws_cfg["aws_secret_access_key"].strip()
        if key_id.upper() in ("YOUR_AWS_ACCESS_KEY_ID", "", "PLACEHOLDER") or \
           secret.upper() in ("YOUR_AWS_SECRET_ACCESS_KEY", "", "PLACEHOLDER"):
            raise ValueError(
                "AWS credentials are not configured. "
                "Please update aws_access_key_id and aws_secret_access_key in the pipeline credentials."
            )
        create_stage_sql = f"""
        CREATE OR REPLACE STAGE {stage_full_name}
        URL = 's3://{aws_cfg["s3_bucket_name"]}/'
        CREDENTIALS = (
            AWS_KEY_ID = '{key_id}'
            AWS_SECRET_KEY = '{secret}'
        )
        FILE_FORMAT = (TYPE = PARQUET)
        """
    elif cloud.lower() == "azure":
        azure_cfg = config["azure"]
        create_stage_sql = f"""
        CREATE OR REPLACE STAGE {stage_full_name}
        URL = 'azure://{azure_cfg["storage_account"]}.blob.core.windows.net/{azure_cfg["container_name"]}'
        CREDENTIALS = (
            AZURE_SAS_TOKEN = '?{azure_cfg["azure_sas_token"]}'
        )
        FILE_FORMAT = (TYPE = PARQUET)
        """
    else:
        raise ValueError(f"Unsupported Snowflake cloud stage: {cloud}")

    cursor = target_conn.cursor()
    try:
        cursor.execute(f"CREATE SCHEMA IF NOT EXISTS {target_db}.{stage_schema}")
        cursor.execute(create_stage_sql)
    finally:
        cursor.close()



def _snowflake_raw_type(data_type, precision, scale):
    data_type = str(data_type).upper()
    if "TIMESTAMP" in data_type or data_type == "DATE":
        return "VARCHAR"
    if data_type == "NUMBER" and precision is not None:
        return f"NUMBER({int(precision)},{int(scale or 0)})"
    if data_type in {"TEXT", "VARCHAR"}:
        return "VARCHAR"
    return data_type


def create_incremental_raw_objects(
    target,
    cloud,
    target_conn,
    config_path,
    database,
    schema,
    table,
):
    """
    Create only incremental RAW objects.

    RAW mirrors target business columns. No audit columns are created.
    """
    safe_table = table.replace("/", "_")

    if target == "snowflake":
        raw_db = get_raw_db(database)
        target_db = database
        cursor = target_conn.cursor()
        try:
            _create_snowflake_stage(target_conn, config_path, cloud, database)
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS {raw_db}")
            cursor.execute(f"CREATE SCHEMA IF NOT EXISTS {raw_db}.{schema}")
            cursor.execute(f"""
                SELECT COLUMN_NAME, DATA_TYPE, NUMERIC_PRECISION, NUMERIC_SCALE
                FROM {target_db}.INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_SCHEMA = '{schema.upper()}'
                AND TABLE_NAME = '{safe_table.upper()}'
                ORDER BY ORDINAL_POSITION
            """)
            target_columns = cursor.fetchall()
            if not target_columns:
                raise Exception(f"Target table not found: {target_db}.{schema}.{safe_table}")

            raw_columns = [
                f"{name} {_snowflake_raw_type(data_type, precision, scale)}"
                for name, data_type, precision, scale in target_columns
            ]

            cursor.execute(f"DROP TABLE IF EXISTS {raw_db}.{schema}.{safe_table}")
            cursor.execute(f"""
                CREATE TABLE {raw_db}.{schema}.{safe_table} (
                    {", ".join(raw_columns)}
                )
            """)
            return True
        finally:
            cursor.close()

    if target == "databricks":
        config = parse_config(config_path)
        managed_location = config["databricks"].get("managed_location")
        raw_catalog = f"{database}_stg"
        target_catalog = database

        def create_catalog_sql(catalog):
            if managed_location:
                return f"CREATE CATALOG IF NOT EXISTS {catalog} MANAGED LOCATION '{managed_location}/{catalog}'"
            return f"CREATE CATALOG IF NOT EXISTS {catalog}"

        cursor = target_conn.cursor()
        try:
            cursor.execute(create_catalog_sql(raw_catalog))
            cursor.execute(f"CREATE SCHEMA IF NOT EXISTS {raw_catalog}.{schema}")
            cursor.execute(f"DROP TABLE IF EXISTS {raw_catalog}.{schema}.{safe_table}")
            cursor.execute(
                f"CREATE TABLE {raw_catalog}.{schema}.{safe_table} "
                f"LIKE {target_catalog}.{schema}.{safe_table}"
            )
            return True
        finally:
            cursor.close()

    if target == "bigquery":
        config = parse_config(config_path)
        dataset_location = config["bigquery"].get("dataset_location", "US")
        raw_dataset_id = f"{database.lower()}_stg"
        target_table_id = f"{target_conn.project}.{database.lower()}.{safe_table.lower()}"
        raw_table_id = f"{target_conn.project}.{raw_dataset_id}.{safe_table.lower()}"

        raw_dataset = bigquery.Dataset(f"{target_conn.project}.{raw_dataset_id}")
        raw_dataset.location = dataset_location
        target_conn.create_dataset(raw_dataset, exists_ok=True)

        target_table = target_conn.get_table(target_table_id)
        raw_table = bigquery.Table(raw_table_id, schema=target_table.schema)
        try:
            target_conn.delete_table(raw_table_id, not_found_ok=True)
        except TypeError:
            try:
                target_conn.delete_table(raw_table_id)
            except Exception:
                pass
        target_conn.create_table(raw_table, exists_ok=True)
        return True

    raise ValueError(f"Unsupported target system for incremental raw creation: {target}")


# ─────────────────────────────────────────────────────────────────────────────
# Full Load Database Object Creation Functions
# ─────────────────────────────────────────────────────────────────────────────

SNOWFLAKE_TEMPORAL_SOURCE_TYPES = {
    "date",
    "datetime",
    "datetime2",
    "smalldatetime",
    "datetimeoffset",
    "timestamp",
    "timestamp without time zone",
    "timestamp with time zone",
    "timestamp with local time zone",
    "time",
}


def normalize_source_system(source_system: str) -> str:
    if source_system in {"sapsqlserver", "sqlserver"}:
        return "sqlserver"

    return source_system


def load_type_mapping(mapping_path, source_system, target_system):
    mapping = pd.read_csv(mapping_path)

    source_column = normalize_source_system(source_system).upper()
    target_column = target_system.upper()

    mapping[source_column] = mapping[source_column].astype(str).str.strip().str.lower()
    mapping[target_column] = mapping[target_column].astype(str).str.strip()

    return dict(zip(mapping[source_column], mapping[target_column]))


def create_databricks_objects(
        source_system,
        Source_Conn,
        cloud,
        target_conn, 
        config_path, 
        mapping_path, 
        database, 
        schema, 
        table
):
    """
    Creates RAW and TARGET catalogs, schemas, and tables in Databricks
    Supports AWS & Azure environments.
    """

    cursor = None

    try:
        logger.info(f"Starting Databricks object creation for {database}.{schema}.{table}")
        try:
            config = parse_config(config_path)
            db_cfg = config["databricks"]
        except Exception as e:
            logger.error(f"Error reading config file: {config_path} | Error: {str(e)}")
            raise

       
        cloud = db_cfg.get("cloud", "aws").lower()
        managed_location = db_cfg.get("managed_location")

        raw_catalog = f"{database}_stg"
        tgt_catalog = database  # Exact database name — no suffix
        
        # Azure must have managed location
        if cloud == "azure" and not managed_location:
            raise Exception("Azure Databricks requires 'managed_location' in config")

        # Fetch Source Schema
        try:
            query = build_source_columns_query(source_system, database, schema, table)
            columns_df = pd.read_sql(query, Source_Conn)

            if columns_df.empty:
                raise Exception(f"No columns found for {schema}.{table}")

            logger.info(f"Information Schema fetched successfully")
        except Exception as e:
            logger.error(f"Failed to fetch source schema | Error: {str(e)}")
            raise

        # Load Datatype Mapping
        try:
            mapping_dict = load_type_mapping(mapping_path, source_system, "databricks")
        except Exception as e:
            logger.error(f"Error loading mapping file: {mapping_path} | Error: {str(e)}")
            raise

        # Build Column Definitions
        try:
            base_columns = []

            for _, col in columns_df.iterrows():
                col_name = col["COLUMN_NAME"].replace("/", "_")
                dtype = col["DATA_TYPE"].lower()

                db_type = mapping_dict.get(dtype, "STRING")
                base_columns.append(f"{col_name} {db_type}")

        except Exception as e:
            logger.error(f"Error while building column definitions | Error: {str(e)}")
            raise

        raw_columns = base_columns
        tgt_columns = base_columns
        
        raw_column_sql = ",\n".join(raw_columns)
        tgt_column_sql = ",\n".join(tgt_columns)

        safe_table = table.replace("/", "_")

        cursor = target_conn.cursor()

        # CREATE CATALOGS
        def create_catalog_sql(cloud, catalog_name):
            if cloud == "azure":
                return f"""
                CREATE CATALOG IF NOT EXISTS {catalog_name}
                MANAGED LOCATION '{managed_location}/{catalog_name}'
                """
            elif managed_location:
                return f"""
                CREATE CATALOG IF NOT EXISTS {catalog_name}
                MANAGED LOCATION '{managed_location}/{catalog_name}'
                """
            else:
                return f"CREATE CATALOG IF NOT EXISTS {catalog_name}"

        try:
            cursor.execute(create_catalog_sql(cloud, raw_catalog))
            cursor.execute(create_catalog_sql(cloud, tgt_catalog))

            # CREATE SCHEMAS
            cursor.execute(f"CREATE SCHEMA IF NOT EXISTS {raw_catalog}.{schema}")
            cursor.execute(f"CREATE SCHEMA IF NOT EXISTS {tgt_catalog}.{schema}")

            # CREATE RAW TABLE
            control_schema = "control_schema"
            cursor.execute(f"CREATE SCHEMA IF NOT EXISTS {tgt_catalog}.{control_schema}")

            create_raw_table = f"""
            CREATE TABLE IF NOT EXISTS {raw_catalog}.{schema}.{safe_table} (
            {raw_column_sql}
            )
            USING DELTA
            """
            cursor.execute(create_raw_table)

            # CREATE TARGET TABLE
            create_tgt_table = f"""
            CREATE TABLE IF NOT EXISTS {tgt_catalog}.{schema}.{safe_table} (
            {tgt_column_sql}
            )
            USING DELTA
            """
            cursor.execute(create_tgt_table)

            logger.info(f"RAW table created: {raw_catalog}.{schema}.{table}")
            logger.info(f"TGT table created: {tgt_catalog}.{schema}.{table}")

        except Exception as e:
            logger.error(f"Failed during Databricks object creation | Error: {str(e)}")
            raise
        
        return True

    except Exception as e:
        logger.error(f"Error: {str(e)}")
        raise

    finally:
        if cursor:
            cursor.close()
            logger.info("Cursor closed")  


def create_snowflake_objects(
    source_system,
    Source_Conn,
    cloud,
    target_conn,
    config_path,
    mapping_path,
    database,
    schema,
    table
):
    """
    Creates Snowflake objects:
    - Database
    - Schema
    - Table
    - External Stage (S3/Azure)
    """
    cursor = None

    try:
        logger.info(f"Starting Snowflake object creation for {database}.{schema}.{table}")
        
        try:
            config = parse_config(config_path)
            sf_cfg = config["snowflake"]
        except Exception as e:
            logger.error(f"Error reading config file: {config_path} | Error: {str(e)}")
            raise
        
        sf_database = sf_cfg["database"]
        sf_schema = "cloud_stage"
        
        # Fetch source table schema from SQL Server
        try:
            query = build_source_columns_query(source_system, database, schema, table)
            columns_df = pd.read_sql(query, Source_Conn)

            logger.info(f"Retrieved source schema:\n{columns_df}")

            if columns_df.empty:
                raise Exception(f"Schema not found for {schema}.{table}")

        except Exception as e:
            logger.error(f"Error fetching schema from source | Error: {str(e)}")
            raise

        raw_db = get_raw_db(sf_database)
        tgt_db = get_target_db(sf_database)
        safe_table = table.replace("/", "_")

        stage_name = "stagename"
        stage_full_name = f"{tgt_db}.{sf_schema}.{stage_name}"

        try:
            if cloud.lower() == "aws":
                aws_cfg = config["aws"]
                aws_key = aws_cfg["aws_access_key_id"]
                aws_secret = aws_cfg["aws_secret_access_key"]
                s3_bucket = aws_cfg["s3_bucket_name"]
                s3_url = f"s3://{s3_bucket}/"
                
                create_stage_sql = f"""
                        CREATE OR REPLACE STAGE {stage_full_name}
                        URL = '{s3_url}'
                        CREDENTIALS = (
                            AWS_KEY_ID = '{aws_key}'
                            AWS_SECRET_KEY = '{aws_secret}'
                        )
                        FILE_FORMAT = (TYPE = PARQUET)
                        """

            elif cloud.lower() == "azure":
                azure_cfg = config["azure"]
                AZURE_SAS_TOKEN = azure_cfg["azure_sas_token"]
                container_name = azure_cfg["container_name"]
                storage_account = azure_cfg["storage_account"]

                create_stage_sql = f"""
                        CREATE OR REPLACE STAGE {stage_full_name}
                        URL = 'azure://{storage_account}.blob.core.windows.net/{container_name}'
                        CREDENTIALS = (
                            AZURE_SAS_TOKEN = '?{AZURE_SAS_TOKEN}'
                        )
                        FILE_FORMAT = (TYPE = PARQUET);
                        """
        
        except Exception as e:
            logger.error(f"Error building stage SQL | Error: {str(e)}")
            raise       

        # Load datatype mapping
        try:
            mapping_dict = load_type_mapping(mapping_path, source_system, "snowflake")
        except Exception as e:
            logger.error(f"Error loading mapping file: {mapping_path} | Error: {str(e)}")
            raise
 
        # Build column definitions
        try:
            raw_columns = []
            tgt_columns = []

            for _, col in columns_df.iterrows():
                col_name = col["COLUMN_NAME"].replace("/", "_")
                dtype = col["DATA_TYPE"].lower()

                sf_type = mapping_dict.get(dtype, "STRING")

                if sf_type is None or sf_type.lower() == "nan":
                    raise Exception(f"Missing datatype mapping for: {dtype}")

                raw_type = "VARCHAR" if dtype in SNOWFLAKE_TEMPORAL_SOURCE_TYPES else sf_type

                raw_columns.append(f"{col_name} {raw_type}")
                tgt_columns.append(f"{col_name} {sf_type}")

            raw_columns_sql = ",\n".join(raw_columns)
            tgt_columns_sql = ",\n".join(tgt_columns)

        except Exception as e:
            logger.error(f"Error building column definitions | Error: {str(e)}")
            raise

        try:
            cursor = target_conn.cursor()

            logger.info(f"Creating snowflake Database {sf_database} ")
            
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS {raw_db}")
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS {tgt_db}")

            cursor.execute(f"CREATE SCHEMA IF NOT EXISTS {tgt_db}.{sf_schema}")
            cursor.execute(f"CREATE SCHEMA IF NOT EXISTS {raw_db}.{schema}")
            cursor.execute(f"CREATE SCHEMA IF NOT EXISTS {tgt_db}.{schema}")

            cursor.execute(create_stage_sql)

            cursor.execute(f"DROP TABLE IF EXISTS {raw_db}.{schema}.{safe_table}")
            cursor.execute(f"DROP TABLE IF EXISTS {tgt_db}.{schema}.{safe_table}")

            create_raw_sql = f"""
            CREATE TABLE {raw_db}.{schema}.{safe_table} (
            {raw_columns_sql}
            )
            """
            cursor.execute(create_raw_sql)

            create_tgt_sql = f"""
            CREATE TABLE {tgt_db}.{schema}.{safe_table} (
            {tgt_columns_sql}
            )
            """
            cursor.execute(create_tgt_sql)

            cursor.close()
            logger.info("RAW & TGT objects created successfully")
        except Exception as e:
            logger.error(f"Error executing Snowflake SQL | Error: {str(e)}")
            raise

        return True

    except Exception as e:
        logger.info(f"Error creating Snowflake objects: {str(e)}")
        raise Exception(f"Error creating Snowflake objects: {str(e)}") 
     
    finally:
        if cursor:
            cursor.close()
            logger.info("Cursor closed")
    

def create_bigquery_objects(
    source_system,
    source_conn,
    bq_client,
    config_path,
    mapping_path,
    database,
    schema,
    table
):
    try:
        logger.info(f"Creating BigQuery objects for {database}.{table}")

        # Get Source Column Metadata
        try:
            query = build_source_columns_query(source_system, database, schema, table)
            df = pd.read_sql(query, source_conn)

            if df.empty:
                raise Exception(f"Schema not found for {schema}.{table}")

        except Exception as e:
            logger.info(f"Schema fetch failed: {str(e)}")
            raise

        # Load Mapping
        try:
            mapping_dict = load_type_mapping(mapping_path, source_system, "bigquery")
        except Exception as e:
            logger.info(f"Mapping load failed: {str(e)}")
            raise

        # Build Base Columns
        try:
            base_fields = []

            for _, row in df.iterrows():
                col = row["COLUMN_NAME"].lower().replace("/", "_")
                dtype = str(row["DATA_TYPE"]).lower()

                bq_type = mapping_dict.get(dtype, "STRING")

                if bq_type is None or str(bq_type).lower() == "nan":
                    raise Exception(f"Missing datatype mapping for: {dtype}")

                base_fields.append(bigquery.SchemaField(col, bq_type))

        except Exception as e:
            logger.info(f"Column build failed: {str(e)}")
            raise

        raw_fields = base_fields
        tgt_fields = base_fields

        # CREATE DATASETS
        try:
            config = parse_config(config_path)
            bq_cfg = config["bigquery"]

            raw_dataset_id = f"{database.lower()}_stg"
            tgt_dataset_id = database.lower()  # Exact database name — no suffix

            raw_dataset_ref = f"{bq_client.project}.{raw_dataset_id}"
            tgt_dataset_ref = f"{bq_client.project}.{tgt_dataset_id}"

            raw_dataset = bigquery.Dataset(raw_dataset_ref)
            raw_dataset.location = bq_cfg.get("dataset_location", "US")

            tgt_dataset = bigquery.Dataset(tgt_dataset_ref)
            tgt_dataset.location = bq_cfg.get("dataset_location", "US")

            bq_client.create_dataset(raw_dataset, exists_ok=True)
            bq_client.create_dataset(tgt_dataset, exists_ok=True)

            logger.info(f"Datasets ready: {raw_dataset_id}, {tgt_dataset_id}")

        except Exception as e:
            logger.info(f"Dataset creation failed: {str(e)}")
            raise

        # CREATE TABLES
        try:
            table = table.lower().replace("/", "_")

            raw_table_id = f"{bq_client.project}.{raw_dataset_id}.{table}"
            tgt_table_id = f"{bq_client.project}.{tgt_dataset_id}.{table}"

            raw_table = bigquery.Table(raw_table_id, schema=raw_fields)
            tgt_table = bigquery.Table(tgt_table_id, schema=tgt_fields)

            bq_client.create_table(raw_table, exists_ok=True)
            bq_client.create_table(tgt_table, exists_ok=True)

            logger.info(f"Tables created in BigQuery: RAW={raw_table_id}, TGT={tgt_table_id}")

        except Exception as e:
            logger.info(f"Table creation failed: {str(e)}")
            raise

        logger.info("BigQuery objects created successfully")
        return True

    except Exception as e:
        logger.info(f"BigQuery object creation failed: {str(e)}")
        raise
