import pandas as pd
from src.parse_config import parse_config
from src.custom_logger import get_logger
from google.cloud import bigquery
from src.data_extraction import build_source_columns_query
from src.connections import get_snowflake_stage_schema
logger = get_logger()

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

        raw_catalog = f"{database}_raw"
        tgt_catalog = f"{database}_tgt"
        
        # 🔴 IMPORTANT FIX: Azure must have managed location
        if cloud == "azure" and not managed_location:
            raise Exception("Azure Databricks requires 'managed_location' in config")

        # --------------------------------------------------
        # Fetch Source Schema
        # --------------------------------------------------
        try:
            query = build_source_columns_query(source_system, database, schema, table)
            columns_df = pd.read_sql(query, Source_Conn)

            if columns_df.empty:
                raise Exception(f"No columns found for {schema}.{table}")

            logger.info(f"Information Schema fetched successfully")
        except Exception as e:
            logger.error(f"Failed to fetch source schema | Error: {str(e)}")
            raise

        # --------------------------------------------------
        # Load Datatype Mapping
        # --------------------------------------------------
        try:
            mapping_dict = load_type_mapping(mapping_path, source_system, "databricks")
        except Exception as e:
            logger.error(f"Error loading mapping file: {mapping_path} | Error: {str(e)}")
            raise

        # --------------------------------------------------
        # Build Column Definitions
        # --------------------------------------------------
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
        
        # RAW & TARGET columns
        raw_column_sql = ",\n".join(raw_columns)
        tgt_column_sql = ",\n".join(tgt_columns)

        safe_table = table.replace("/", "_")

        cursor = target_conn.cursor()

        # =============================
        # CREATE CATALOGS
        # =============================
        def create_catalog_sql(cloud,catalog_name):
            # Azure → always needs managed location
            if cloud == "azure":
                return f"""
                CREATE CATALOG IF NOT EXISTS {catalog_name}
                MANAGED LOCATION '{managed_location}/{catalog_name}'
                """
            # AWS → optional managed location
            elif managed_location:
                return f"""
                CREATE CATALOG IF NOT EXISTS {catalog_name}
                MANAGED LOCATION '{managed_location}/{catalog_name}'
                """
            else:
                return f"CREATE CATALOG IF NOT EXISTS {catalog_name}"

        try:
            cursor.execute(create_catalog_sql(cloud,raw_catalog))
            cursor.execute(create_catalog_sql(cloud,tgt_catalog))

            # =============================
            # CREATE SCHEMAS
            # =============================
            cursor.execute(f"CREATE SCHEMA IF NOT EXISTS {raw_catalog}.{schema}")
            cursor.execute(f"CREATE SCHEMA IF NOT EXISTS {tgt_catalog}.{schema}")

            # =============================
            # CREATE RAW TABLE
            # =============================
            control_schema = f"{database}_stg"

            # 🔥 CREATE FIRST
            cursor.execute(f"CREATE SCHEMA IF NOT EXISTS {tgt_catalog}.{control_schema}")


            create_raw_table = f"""
            CREATE TABLE IF NOT EXISTS {raw_catalog}.{schema}.{safe_table} (
            {raw_column_sql}
            )
            USING DELTA
            """

            cursor.execute(create_raw_table)

        

            # =============================
            # CREATE TARGET TABLE
            # =============================

            create_tgt_table = f"""
            CREATE TABLE IF NOT EXISTS {tgt_catalog}.{schema}.{safe_table} (
            {tgt_column_sql}
            )
            USING DELTA
            """

            cursor.execute(create_tgt_table)

            logger.info(f"RAW table created: {raw_catalog}.{schema}.{table}")
            logger.info(f"TGT table created: {tgt_catalog}.{schema}.{table}")

            print(f"RAW Table: {raw_catalog}.{schema}.{table}")
            print(f"TGT Table: {tgt_catalog}.{schema}.{table}")


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
        
        # --------------------------------------------------
        # Load Snowflake config
        # --------------------------------------------------
        try:
            config = parse_config(config_path)
            sf_cfg = config["snowflake"]
        except Exception as e:
            logger.error(f"Error reading config file: {config_path} | Error: {str(e)}")
            raise
        
 
        sf_database = sf_cfg["database"]
        sf_schema = get_snowflake_stage_schema(sf_database)
        

        
        # --------------------------------------------------
        # Fetch source table schema from SQL Server
        # --------------------------------------------------
        try:
            query = build_source_columns_query(source_system, database, schema, table)
            columns_df = pd.read_sql(query, Source_Conn)

            logger.info(f"Retrieved source schema:\n{columns_df}")

            if columns_df.empty:
                raise Exception(f"Schema not found for {schema}.{table}")

        except Exception as e:
            logger.error(f"Error fetching schema from source | Error: {str(e)}")
            raise

        # -------------------------------
        # database & object names
        # -------------------------------
        raw_db = f"{sf_database}_RAW"
        tgt_db = f"{sf_database}_TGT"
        schema = schema
        safe_table = table.replace("/", "_")

        stage_name = f"external_{cloud}_stage"
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
        # --------------------------------------------------
        # Load datatype mapping
        # --------------------------------------------------
        try:
            mapping_dict = load_type_mapping(mapping_path, source_system, "snowflake")
        except Exception as e:
            logger.error(f"Error loading mapping file: {mapping_path} | Error: {str(e)}")
            raise
 
        # --------------------------------------------------
        # Build column definitions
        # --------------------------------------------------
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

        # --------------------------------------------------
        # STEP 9 — Execute Snowflake SQL (DB, Schema, Tables)
        # --------------------------------------------------
        try:
            cursor = target_conn.cursor()

            logger.info(f"Creating snwoflake Database {sf_database} ")
            
            # -------------------------------
            # Create Databases
            # -------------------------------
            logger.info(f"Creating RAW DB: {raw_db}")
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS {raw_db}")

            logger.info(f"Creating TGT DB: {tgt_db}")
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS {tgt_db}")

            # -------------------------------
            # Create Schemas
            # -------------------------------
            cursor.execute(f"CREATE SCHEMA IF NOT EXISTS {tgt_db}.{sf_schema}")
            cursor.execute(f"CREATE SCHEMA IF NOT EXISTS {raw_db}.{schema}")
            cursor.execute(f"CREATE SCHEMA IF NOT EXISTS {tgt_db}.{schema}")

            
            # -------------------------------
            # Create Stage (in RAW DB)
            # -------------------------------
            logger.info(f"Creating Stage: {stage_full_name}")
            cursor.execute(create_stage_sql)

            # -------------------------------
            # Recreate RAW/TGT tables for full-load correctness.
            # This prevents stale column types from earlier runs from
            # silently surviving under CREATE TABLE IF NOT EXISTS.
            # -------------------------------
            logger.info(f"Dropping RAW table if exists: {raw_db}.{schema}.{safe_table}")
            cursor.execute(f"DROP TABLE IF EXISTS {raw_db}.{schema}.{safe_table}")

            logger.info(f"Dropping TGT table if exists: {tgt_db}.{schema}.{safe_table}")
            cursor.execute(f"DROP TABLE IF EXISTS {tgt_db}.{schema}.{safe_table}")

            create_raw_sql = f"""
            CREATE TABLE {raw_db}.{schema}.{safe_table} (
            {raw_columns_sql}
            )
            """

            logger.info(f"Creating RAW table {raw_db}.{schema}.{safe_table}")
            cursor.execute(create_raw_sql)

            # -------------------------------
            # Create TGT Table
            # -------------------------------
            create_tgt_sql = f"""
            CREATE TABLE {tgt_db}.{schema}.{safe_table} (
            {tgt_columns_sql}
            )
            """

            logger.info(f"Creating TGT table {tgt_db}.{schema}.{safe_table}")
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

    raw_dataset_id = None
    tgt_dataset_id = None

    try:
        logger.info(f"Creating BigQuery objects for {database}.{table}")

        # ---------------------------------------------
        # Get Source Column Metadata
        # ---------------------------------------------
        try:
            query = build_source_columns_query(source_system, database, schema, table)
            df = pd.read_sql(query, source_conn)

            if df.empty:
                raise Exception(f"Schema not found for {schema}.{table}")

        except Exception as e:
            logger.info(f"Schema fetch failed: {str(e)}")
            raise

        # ---------------------------------------------
        # Load Mapping
        # ---------------------------------------------
        try:
            mapping_dict = load_type_mapping(mapping_path, source_system, "bigquery")
        except Exception as e:
            logger.info(f"Mapping load failed: {str(e)}")
            raise

        # ---------------------------------------------
        # Build Base Columns (LOWERCASE)
        # ---------------------------------------------
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

        # ---------------------------------------------
        # RAW & TGT SCHEMA
        # ---------------------------------------------
        raw_fields = base_fields
        tgt_fields = base_fields

        # ---------------------------------------------
        # CREATE DATASETS (RAW & TGT)
        # ---------------------------------------------
        try:
            # Load BigQuery-specific config (mainly dataset location)
            config = parse_config(config_path)
            bq_cfg = config["bigquery"]

            # Define dataset names for RAW (staging) and TGT (final processed data)
            raw_dataset_id = f"{database.lower()}_raw"
            tgt_dataset_id = f"{database.lower()}_tgt"

            # Fully qualified dataset references (project.dataset)
            raw_dataset_ref = f"{bq_client.project}.{raw_dataset_id}"
            tgt_dataset_ref = f"{bq_client.project}.{tgt_dataset_id}"

            # Initialize dataset objects and assign location (default = US if not provided)
            raw_dataset = bigquery.Dataset(raw_dataset_ref)
            raw_dataset.location = bq_cfg.get("dataset_location", "US")

            tgt_dataset = bigquery.Dataset(tgt_dataset_ref)
            tgt_dataset.location = bq_cfg.get("dataset_location", "US")

            # Create datasets if they don’t already exist (idempotent operation)
            bq_client.create_dataset(raw_dataset, exists_ok=True)
            bq_client.create_dataset(tgt_dataset, exists_ok=True)

            logger.info(f"Datasets ready: {raw_dataset_id}, {tgt_dataset_id}")

        except Exception as e:
            logger.info(f"Dataset creation failed: {str(e)}")
            raise
        # ---------------------------------------------
        # CREATE TABLES
        # ---------------------------------------------
        try:
            # Clean table name to ensure compatibility (BigQuery doesn't allow '/')
            table = table.lower().replace("/", "_")

            # Fully qualified table IDs (project.dataset.table)
            raw_table_id = f"{bq_client.project}.{raw_dataset_id}.{table}"
            tgt_table_id = f"{bq_client.project}.{tgt_dataset_id}.{table}"

            # Define table objects with corresponding schemas
            raw_table = bigquery.Table(raw_table_id, schema=raw_fields)
            tgt_table = bigquery.Table(tgt_table_id, schema=tgt_fields)

            # Create tables if not exists (safe for re-runs)
            bq_client.create_table(raw_table, exists_ok=True)
            bq_client.create_table(tgt_table, exists_ok=True)

            # Log final output for traceability
            logger.info(f"Tables created:")
            logger.info(f"RAW → {raw_table_id}")
            logger.info(f"TGT → {tgt_table_id}")

        except Exception as e:
            logger.info(f"Table creation failed: {str(e)}")
            raise

        logger.info("BigQuery objects created successfully")
        return True

    except Exception as e:
        logger.info(f"BigQuery object creation failed: {str(e)}")
        raise
