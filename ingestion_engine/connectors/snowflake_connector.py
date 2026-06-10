import snowflake.connector


class SnowflakeConnector:

    def __init__(self, user, password, account, warehouse, database, schema):
        self.conn = snowflake.connector.connect(
            user=user,
            password=password,
            account=account,
            warehouse=warehouse,
            database=database
        )

    def get_connection(self):
        return self.conn
 
    def fetch_table_metadata(self, schema_name, table_name):
        query = f"""
        SELECT 
            COLUMN_NAME,
            DATA_TYPE,
            CHARACTER_MAXIMUM_LENGTH,
            NUMERIC_PRECISION,
            NUMERIC_SCALE,
            ORDINAL_POSITION,
            IS_NULLABLE
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = '{schema_name}'
        AND TABLE_NAME = '{table_name}'
        ORDER BY ORDINAL_POSITION
        """
        cursor = self.conn.cursor()
        cursor.execute(query)
        rows = cursor.fetchall()

        metadata = []
        for row in rows:
            metadata.append({
                "column_name": row[0].lower(),
                "data_type": row[1].lower(),
                "char_length": row[2],
                "precision": row[3],
                "scale": row[4],
                "ordinal_position": row[5],
                "nullable": row[6]
            })
        return metadata
    
    def fetch_schemas(self):
        query = """
            select SCHEMA_NAME from information_schema.schemata
            where schema_name  <> 'INFORMATION_SCHEMA'
"""
        cursor = self.conn.cursor()
        cursor.execute(query)
        rows = cursor.fetchall()
        schemas = [row[0] for row in rows]
        return schemas

    def fetch_tables(self, schema_name):
        query = f"SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_SCHEMA = '{schema_name.upper()}'"
        cursor = self.conn.cursor()
        cursor.execute(query)
        rows = cursor.fetchall()
        tables = [row[0] for row in rows]
        return tables
