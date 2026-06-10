import pyodbc


class SQLServerConnector:

    def __init__(self, server, database, username, password):
        self.connection_string = (
            f"DRIVER={{ODBC Driver 17 for SQL Server}};"
            f"SERVER={server},1433;"
            f"DATABASE={database};"
            f"UID={username};"
            f"PWD={password};"
            f"TrustServerCertificate=yes;"
        )
        self.conn = None

    def connect(self):
        self.conn = pyodbc.connect(self.connection_string)

    def fetch_table_metadata(self, schema_name, table_name):
        pk_query = f"""
        SELECT kcu.COLUMN_NAME
        FROM INFORMATION_SCHEMA.TABLE_CONSTRAINTS tc 
        JOIN INFORMATION_SCHEMA.KEY_COLUMN_USAGE kcu 
            ON tc.CONSTRAINT_NAME = kcu.CONSTRAINT_NAME AND tc.TABLE_SCHEMA = kcu.TABLE_SCHEMA AND tc.TABLE_NAME = kcu.TABLE_NAME
        WHERE tc.TABLE_SCHEMA = '{schema_name}'
        AND tc.TABLE_NAME = '{table_name}' 
        AND tc.CONSTRAINT_TYPE = 'PRIMARY KEY'
        """
        cursor = self.conn.cursor()
        cursor.execute(pk_query)
        pk_rows = cursor.fetchall()
        pks = [row[0].lower() for row in pk_rows]

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
        cursor.execute(query)
        rows = cursor.fetchall()

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
    
    def fetch_schemas(self):
        query = "SELECT name FROM sys.schemas"
        cursor = self.conn.cursor()
        cursor.execute(query)
        rows = cursor.fetchall()
        schemas = [row[0] for row in rows]
        return schemas

    def fetch_tables(self, schema_name):
        query = f"SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_SCHEMA = '{schema_name}' AND TABLE_TYPE = 'BASE TABLE'"
        cursor = self.conn.cursor()
        cursor.execute(query)
        rows = cursor.fetchall()
        tables = [row[0] for row in rows]
        return tables