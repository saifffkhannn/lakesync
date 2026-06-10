import logging
from databricks import sql

logger = logging.getLogger("data_accelerator")

class DatabricksConnector:
    def __init__(self, server_hostname, http_path, access_token, catalog=None):
        self.server_hostname = server_hostname
        self.http_path = http_path
        self.access_token = access_token
        self.catalog = catalog
        self.connection = sql.connect(
                server_hostname=server_hostname,
                http_path=http_path,
                access_token=access_token
            )
    
    def get_connection(self):
        try:
            return self.connection
        except Exception as e:
            logger.error(f"Failed to connect to Databricks SQL: {e}")
            raise

    def fetch_schemas(self):
        # schema_table_map = {}
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(f"USE CATALOG {self.catalog}")

        cursor.execute("SHOW SCHEMAS")
        schemas = [row[0] for row in cursor.fetchall()]
        return schemas

    def fetch_tables(self, schema: str):
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute(f"SHOW TABLES IN {self.catalog}.{schema}")
            tables = [row[1] for row in cursor.fetchall()]
            return tables
        except Exception as e:
            logger.error(f"Failed to fetch Databricks tables for {schema}: {e}")
            return []

    def fetch_table_metadata(self, schema: str, table: str):
        try:
            query = f"""
            SELECT 
                COLUMN_NAME,
                DATA_TYPE,
                CHARACTER_MAXIMUM_LENGTH,
                NUMERIC_PRECISION,
                NUMERIC_SCALE,
                ORDINAL_POSITION,
                IS_NULLABLE
            FROM {self.catalog}.INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = '{schema}'
            AND TABLE_NAME = '{table}'
            ORDER BY ORDINAL_POSITION
            """
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute(query)
            rows = cursor.fetchall()
            metadata = []
            for row in rows:
                metadata.append({
                    "column_name": row[0],
                    "data_type": row[1],
                    "char_length": row[2],
                    "precision": row[3],
                    "scale": row[4],
                    "ordinal_position": row[5],
                    "nullable": row[6]
                })
            return metadata

        except Exception as e:
            logger.error(f"Failed to fetch Databricks table metadata for {schema}.{table}: {e}")
            return []


# if __name__ == "__main__":
#     server_hostname = ""
#     http_path = ""
#     access_token = ""
#     catalog = ""

#     db = DatabricksConnector(server_hostname, http_path, access_token, catalog)
#     print("\nSchema -> Tables Mapping:")
#     schema_map = db.get_schema_tables_map()
#     print(schema_map)
#     db.print_full_metadata()
