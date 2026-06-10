import mysql.connector


class MySQLConnector:

    def __init__(self, host, port, database, username, password):
        self.host = host
        self.port = int(port)
        self.database = database
        self.username = username
        self.password = password
        self.conn = None

    def connect(self):
        self.conn = mysql.connector.connect(
            host=self.host,
            port=self.port,
            database=self.database,
            user=self.username,
            password=self.password,
            connection_timeout=30
        )

    def fetch_schemas(self):
        query = "SELECT SCHEMA_NAME FROM information_schema.SCHEMATA WHERE SCHEMA_NAME NOT IN ('information_schema','performance_schema','mysql','sys')"
        cursor = self.conn.cursor()
        cursor.execute(query)
        schemas = [row[0] for row in cursor.fetchall()]
        cursor.close()
        return schemas

    def fetch_tables(self, schema_name):
        query = f"SELECT TABLE_NAME FROM information_schema.TABLES WHERE TABLE_SCHEMA = '{schema_name}' AND TABLE_TYPE = 'BASE TABLE'"
        cursor = self.conn.cursor()
        cursor.execute(query)
        tables = [row[0] for row in cursor.fetchall()]
        cursor.close()
        return tables

    def fetch_table_metadata(self, schema_name, table_name):
        pk_query = f"""
        SELECT COLUMN_NAME
        FROM information_schema.KEY_COLUMN_USAGE
        WHERE TABLE_SCHEMA = '{schema_name}'
        AND TABLE_NAME = '{table_name}'
        AND CONSTRAINT_NAME = 'PRIMARY'
        ORDER BY ORDINAL_POSITION
        """
        cursor = self.conn.cursor()
        cursor.execute(pk_query)
        pks = [row[0].lower() for row in cursor.fetchall()]

        query = f"""
        SELECT COLUMN_NAME, DATA_TYPE, CHARACTER_MAXIMUM_LENGTH,
               NUMERIC_PRECISION, NUMERIC_SCALE, ORDINAL_POSITION, IS_NULLABLE
        FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA = '{schema_name}' AND TABLE_NAME = '{table_name}'
        ORDER BY ORDINAL_POSITION
        """
        cursor.execute(query)
        rows = cursor.fetchall()
        cursor.close()

        metadata = []
        for row in rows:
            col_name = row[0].lower()
            metadata.append({
                "column_name": col_name,
                "data_type": row[1].lower(),
                "char_length": row[2],
                "precision": row[3],
                "scale": row[4],
                "ordinal_position": row[5],
                "nullable": row[6],
                "is_primary_key": col_name in pks
            })
        return metadata
