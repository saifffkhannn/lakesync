try:
    import oracledb as cx_Oracle
    _ORACLE_LIB = "oracledb"
except ImportError:
    import cx_Oracle
    _ORACLE_LIB = "cx_Oracle"


class OracleConnector:

    def __init__(self, host, port, service_name, username, password):
        self.host = host
        self.port = int(port)
        self.service_name = service_name
        self.username = username
        self.password = password
        self.conn = None

    def connect(self):
        dsn = f"{self.host}:{self.port}/{self.service_name}"
        if _ORACLE_LIB == "oracledb":
            self.conn = cx_Oracle.connect(
                user=self.username,
                password=self.password,
                dsn=dsn
            )
        else:
            dsn_obj = cx_Oracle.makedsn(self.host, self.port, service_name=self.service_name)
            self.conn = cx_Oracle.connect(self.username, self.password, dsn_obj)

    def fetch_schemas(self):
        query = "SELECT USERNAME FROM all_users ORDER BY USERNAME"
        cursor = self.conn.cursor()
        cursor.execute(query)
        schemas = [row[0] for row in cursor.fetchall()]
        cursor.close()
        return schemas

    def fetch_tables(self, schema_name):
        query = f"SELECT TABLE_NAME FROM all_tables WHERE OWNER = :owner ORDER BY TABLE_NAME"
        cursor = self.conn.cursor()
        cursor.execute(query, owner=schema_name.upper())
        tables = [row[0] for row in cursor.fetchall()]
        cursor.close()
        return tables

    def fetch_table_metadata(self, schema_name, table_name):
        pk_query = """
        SELECT cols.COLUMN_NAME
        FROM all_constraints cons
        JOIN all_cons_columns cols
            ON cons.CONSTRAINT_NAME = cols.CONSTRAINT_NAME
            AND cons.OWNER = cols.OWNER
        WHERE cons.CONSTRAINT_TYPE = 'P'
        AND cons.OWNER = :owner
        AND cons.TABLE_NAME = :table_name
        ORDER BY cols.POSITION
        """
        cursor = self.conn.cursor()
        cursor.execute(pk_query, owner=schema_name.upper(), table_name=table_name.upper())
        pks = [row[0].lower() for row in cursor.fetchall()]

        query = """
        SELECT COLUMN_NAME, DATA_TYPE, CHAR_COL_DECL_LENGTH,
               DATA_PRECISION, DATA_SCALE, COLUMN_ID, NULLABLE
        FROM all_tab_columns
        WHERE OWNER = :owner AND TABLE_NAME = :table_name
        ORDER BY COLUMN_ID
        """
        cursor.execute(query, owner=schema_name.upper(), table_name=table_name.upper())
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
                "nullable": "YES" if row[6] == "Y" else "NO",
                "is_primary_key": col_name in pks
            })
        return metadata
