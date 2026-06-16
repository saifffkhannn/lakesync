import logging
import json
from mdm.connection import ConnectionManager

logger = logging.getLogger("mdm.schema")

class SchemaDeployer:
    @staticmethod
    def deploy_structures(creds: dict):
        conn = ConnectionManager.get_connection(creds)
        try:
            cursor = conn.cursor()
            db = creds.get("database", "").upper()

            # Ensure schemas exist
            cursor.execute(f"CREATE SCHEMA IF NOT EXISTS {db}.BRONZE")
            cursor.execute(f"CREATE SCHEMA IF NOT EXISTS {db}.MDM")

            # Create Config Table
            cursor.execute(f"""
                CREATE TABLE IF NOT EXISTS {db}.BRONZE.SOURCE_MAPPING_CONFIG (
                    CONFIG_ID          NUMBER AUTOINCREMENT PRIMARY KEY,
                    GROUP_NAME         STRING,
                    EXECUTION_SEQ      NUMBER,
                    SOURCE_SYSTEM      STRING NOT NULL,
                    SRC_DATABASE       STRING NOT NULL,
                    STG_SCHEMA         STRING NOT NULL,
                    STG_TABLE          STRING NOT NULL,
                    TGT_DATABASE       STRING NOT NULL,
                    TGT_SCHEMA         STRING NOT NULL,
                    TGT_TABLE          STRING NOT NULL,
                    MERGE_KEY          STRING NOT NULL,
                    STG_MERGE_KEY      STRING NOT NULL,
                    COLUMN_MAPPING     VARIANT NOT NULL,
                    IS_ACTIVE          BOOLEAN DEFAULT TRUE,
                    CREATED_TS         TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
                    STREAM_NAME        STRING
                )
            """)

            # Create Audit Log
            cursor.execute(f"""
                CREATE TABLE IF NOT EXISTS {db}.BRONZE.MERGE_AUDIT_LOG (
                    LOG_ID             NUMBER AUTOINCREMENT PRIMARY KEY,
                    RUN_ID             STRING,
                    GROUP_NAME         STRING,
                    SOURCE_SYSTEM      STRING,
                    STG_TABLE          STRING,
                    TGT_TABLE          STRING,
                    ROWS_INSERTED      NUMBER DEFAULT 0,
                    ROWS_UPDATED       NUMBER DEFAULT 0,
                    STATUS             STRING,
                    ERROR_MESSAGE      STRING,
                    GENERATED_SQL      STRING,
                    STARTED_TS         TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
                    COMPLETED_TS       TIMESTAMP
                )
            """)

            # Create MASTER_ENTITY Table
            cursor.execute(f"""
                CREATE TABLE IF NOT EXISTS {db}.MDM.MASTER_ENTITY (
                    MASTER_ID        VARCHAR,
                    GROUP_NAME       VARCHAR,
                    ENTITY_DATA      VARIANT,
                    SOURCE_IDS       VARCHAR,
                    SOURCE_SYSTEMS   VARCHAR,
                    CLUSTER_SIZE     NUMBER,
                    MATCH_CONFIDENCE VARCHAR,
                    PIPELINE_RUN_ID  VARCHAR,
                    CREATED_TS       TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
                )
            """)
        finally:
            conn.close()

    @staticmethod
    def configure_mapping(creds: dict, config_payload: dict):
        conn = ConnectionManager.get_connection(creds)
        try:
            cursor = conn.cursor()
            db = creds.get("database", "").upper()

            group_name = config_payload.get("group_name", "CUSTOMER_UNIFICATION_MULTI_DB")
            source_system = config_payload.get("source_system", "")
            src_db = config_payload.get("src_db", db)
            stg_schema = config_payload.get("stg_schema", "RAW_STG")
            stg_table = config_payload.get("stg_table", "")
            tgt_schema = config_payload.get("tgt_schema", "BRONZE")
            tgt_table = config_payload.get("tgt_table", "")
            merge_key = config_payload.get("merge_key", "")
            stg_merge_key = config_payload.get("stg_merge_key", "")
            column_mapping = config_payload.get("column_mapping", [])
            stream_name = config_payload.get("stream_name", f"STM_{stg_table}")

            # Enable Change Tracking on Target Table
            try:
                cursor.execute(f"ALTER TABLE {db}.{tgt_schema}.{tgt_table} SET CHANGE_TRACKING = TRUE")
            except Exception as e:
                logger.warning(f"Failed to enable change tracking: {e}")

            # Create Stream if it doesn't exist
            try:
                cursor.execute(f"CREATE STREAM IF NOT EXISTS {db}.{tgt_schema}.{stream_name} ON TABLE {db}.{tgt_schema}.{tgt_table}")
            except Exception as e:
                logger.warning(f"Failed to create stream: {e}")

            # Delete existing mapping config if matching group_name & source_system to overwrite
            cursor.execute(f"""
                DELETE FROM {db}.BRONZE.SOURCE_MAPPING_CONFIG
                WHERE GROUP_NAME = %s AND SOURCE_SYSTEM = %s
            """, (group_name, source_system))

            # Fetch next execution sequence
            cursor.execute(f"SELECT COALESCE(MAX(EXECUTION_SEQ), 0) + 1 FROM {db}.BRONZE.SOURCE_MAPPING_CONFIG WHERE GROUP_NAME = %s", (group_name,))
            next_seq = cursor.fetchone()[0]

            # Insert Config Row
            cursor.execute(f"""
                INSERT INTO {db}.BRONZE.SOURCE_MAPPING_CONFIG
                (GROUP_NAME, EXECUTION_SEQ, SOURCE_SYSTEM, SRC_DATABASE, STG_SCHEMA, STG_TABLE, TGT_DATABASE, TGT_SCHEMA, TGT_TABLE, MERGE_KEY, STG_MERGE_KEY, COLUMN_MAPPING, STREAM_NAME)
                SELECT %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, PARSE_JSON(%s), %s
            """, (group_name, next_seq, source_system, src_db, stg_schema, stg_table, db, tgt_schema, tgt_table, merge_key, stg_merge_key, json.dumps(column_mapping), stream_name))

        finally:
            conn.close()

    @staticmethod
    def replicate_to_bronze(creds: dict, tables: list):
        conn = ConnectionManager.get_connection(creds)
        results = []
        try:
            cursor = conn.cursor()
            for t in tables:
                db = t.get("bronze_database", t.get("database", "")).upper()
                schema = t.get("bronze_schema", "BRONZE").upper()
                table = t.get("bronze_table", f"BRONZE_{t.get('table', '')}").upper()
                col_mapping = t.get("column_mapping", [])

                try:
                    cursor.execute(f"CREATE SCHEMA IF NOT EXISTS {db}.{schema}")
                    
                    columns = []
                    for col in col_mapping:
                        col_name = col.get("tgt", col.get("src", "")).upper()
                        col_type = col.get("type", "VARCHAR").upper()
                        columns.append(f"{col_name} {col_type}")
                    
                    columns.append("SOURCE_SYSTEM VARCHAR")
                    columns.append("LOAD_TIMESTAMP TIMESTAMP_NTZ")
                    columns.append("LAST_MODIFIED_DATE TIMESTAMP_NTZ")
                    
                    columns_sql = ", ".join(columns)
                    cursor.execute(f"CREATE TABLE IF NOT EXISTS {db}.{schema}.{table} ({columns_sql})")
                    
                    results.append({
                        "database": t.get("database"),
                        "schema": t.get("schema"),
                        "table": t.get("table"),
                        "bronze_table": table,
                        "bronze_schema": schema,
                        "bronze_database": db,
                        "status": "SUCCESS"
                    })
                except Exception as table_err:
                    logger.error(f"Failed to create bronze table {db}.{schema}.{table}: {table_err}")
                    results.append({
                        "database": t.get("database"),
                        "schema": t.get("schema"),
                        "table": t.get("table"),
                        "bronze_table": table,
                        "bronze_schema": schema,
                        "bronze_database": db,
                        "status": "FAILED",
                        "error": str(table_err)
                    })
            return results
        finally:
            conn.close()

    @staticmethod
    def configure_batch(creds: dict, group_name: str, configs: list):
        # 1. Deploy structures
        SchemaDeployer.deploy_structures(creds)
        
        # 2. Configure mappings
        for config_payload in configs:
            config_payload["group_name"] = group_name
            SchemaDeployer.configure_mapping(creds, config_payload)
            
        # 3. Deploy procedures
        from mdm.procedures import ProcedureDeployer
        ProcedureDeployer.deploy_procedures(creds)

