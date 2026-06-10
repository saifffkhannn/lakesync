import json
import logging
from mdm.connection import ConnectionManager

logger = logging.getLogger("mdm.queries")

class QueryHandler:
    @staticmethod
    def fetch_tables(creds: dict, schema: str):
        conn = ConnectionManager.get_connection(creds)
        try:
            cursor = conn.cursor()
            db = creds.get("database", "").upper()
            cursor.execute(f"SELECT TABLE_NAME FROM {db}.INFORMATION_SCHEMA.TABLES WHERE TABLE_SCHEMA = '{schema.upper()}'")
            return [row[0] for row in cursor.fetchall()]
        finally:
            conn.close()

    @staticmethod
    def fetch_columns(creds: dict, schema: str, table: str):
        conn = ConnectionManager.get_connection(creds)
        try:
            cursor = conn.cursor()
            db = creds.get("database", "").upper()
            cursor.execute(f"""
                SELECT COLUMN_NAME, DATA_TYPE, CHARACTER_MAXIMUM_LENGTH, NUMERIC_PRECISION, NUMERIC_SCALE, ORDINAL_POSITION, IS_NULLABLE
                FROM {db}.INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_SCHEMA = '{schema.upper()}' AND TABLE_NAME = '{table.upper()}'
                ORDER BY ORDINAL_POSITION
            """)
            rows = cursor.fetchall()
            return [{
                "column_name": row[0],
                "data_type": row[1].lower(),
                "char_length": row[2],
                "precision": row[3],
                "scale": row[4],
                "ordinal_position": row[5],
                "nullable": row[6]
            } for row in rows]
        finally:
            conn.close()

    @staticmethod
    def fetch_audit_logs(creds: dict, group_name: str):
        conn = ConnectionManager.get_connection(creds)
        try:
            cursor = conn.cursor()
            db = creds.get("database", "").upper()
            cursor.execute(f"""
                SELECT LOG_ID, RUN_ID, SOURCE_SYSTEM, STG_TABLE, TGT_TABLE, ROWS_INSERTED, ROWS_UPDATED, STATUS, ERROR_MESSAGE, STARTED_TS
                FROM {db}.BRONZE.MERGE_AUDIT_LOG
                WHERE GROUP_NAME = %s
                ORDER BY STARTED_TS DESC
                LIMIT 50
            """, (group_name,))
            rows = cursor.fetchall()
            return [{
                "log_id": row[0],
                "run_id": row[1],
                "source_system": row[2],
                "stg_table": row[3],
                "tgt_table": row[4],
                "rows_inserted": row[5],
                "rows_updated": row[6],
                "status": row[7],
                "error_message": row[8],
                "timestamp": str(row[9])
            } for row in rows]
        finally:
            conn.close()

    @staticmethod
    def fetch_master_records(creds: dict, group_name: str):
        conn = ConnectionManager.get_connection(creds)
        try:
            cursor = conn.cursor()
            db = creds.get("database", "").upper()
            
            # Check if Master Entity Flat view exists before querying
            try:
                cursor.execute(f"SELECT * FROM {db}.MDM.MASTER_ENTITY_FLAT WHERE GROUP_NAME = %s LIMIT 100", (group_name,))
                columns = [desc[0] for desc in cursor.description]
                rows = cursor.fetchall()
                return [dict(zip(columns, row)) for row in rows]
            except Exception as view_err:
                logger.warning(f"Flat view query failed: {view_err}. Trying direct query.")
                # Fallback to direct query from MASTER_ENTITY
                cursor.execute(f"SELECT MASTER_ID, ENTITY_DATA, SOURCE_IDS, SOURCE_SYSTEMS, CLUSTER_SIZE, MATCH_CONFIDENCE FROM {db}.MDM.MASTER_ENTITY WHERE GROUP_NAME = %s LIMIT 100", (group_name,))
                rows = cursor.fetchall()
                return [{
                    "MASTER_ID": r[0],
                    "ENTITY_DATA": json.loads(r[1]) if isinstance(r[1], str) else r[1],
                    "SOURCE_IDS": r[2],
                    "SOURCE_SYSTEMS": r[3],
                    "CLUSTER_SIZE": r[4],
                    "MATCH_CONFIDENCE": r[5]
                } for r in rows]
        finally:
            conn.close()
