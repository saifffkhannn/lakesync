from src.db_connections import get_Source_connection
from src.data_extractor import query_execution
from src.pipeline_logger import get_logger
from src.config_parser import normalize_platform_name, parse_config
logger = get_logger()


def source_metadata(sourc_platform, config_path):
    """
    Retrieves metadata for source tables including primary key columns.

    Parameters
    ----------
    sourc_platform : str
        Source platform type (e.g., sapsqlserver)
    config_path : str
        Path to configuration file

    Returns
    -------
    DataFrame / Generator
        Metadata containing schema, table name, and primary key columns
    """

    try:
        sourc_platform = normalize_platform_name(sourc_platform)

        if sourc_platform in {"sapsqlserver", "sqlserver"}:
            connection = get_Source_connection(config_path, sourc_platform)
            source_section = "sapsqlserver" if sourc_platform == "sapsqlserver" else "sqlserver"
            source_database = parse_config(config_path)[source_section]["database"]

            # Query to extract primary key metadata
            query = """
            SELECT 
                DB_NAME() AS DB_NAME,
                s.name AS TABLE_SCHEMA,
                t.name AS TABLE_NAME,

                -- Build Primary Key column list
                STUFF((
                    SELECT ', ' + c.name
                    FROM sys.indexes i2
                    INNER JOIN sys.index_columns ic2 
                        ON i2.object_id = ic2.object_id 
                        AND i2.index_id = ic2.index_id
                    INNER JOIN sys.columns c 
                        ON ic2.object_id = c.object_id 
                        AND ic2.column_id = c.column_id
                    WHERE 
                        i2.object_id = t.object_id
                        AND i2.is_primary_key = 1
                    ORDER BY ic2.key_ordinal
                    FOR XML PATH(''), TYPE
                ).value('.', 'NVARCHAR(MAX)'), 1, 2, '') AS PRIMARY_KEY_COLUMNS

            FROM sys.tables t
            INNER JOIN sys.schemas s 
                ON t.schema_id = s.schema_id

            ORDER BY 
                s.name,
                t.name;
            """

            # Execute query and retrieve metadata
            df = query_execution(connection, sourc_platform, query)

            # Close database connection
            connection.close()

            return df

        if sourc_platform == "mysql":
            connection = get_Source_connection(config_path, sourc_platform)
            source_database = parse_config(config_path)["mysql"]["database"]

            query = f"""
            SELECT
                TABLE_SCHEMA AS DB_NAME,
                TABLE_SCHEMA AS TABLE_SCHEMA,
                TABLE_NAME AS TABLE_NAME,
                GROUP_CONCAT(
                    CASE WHEN COLUMN_KEY = 'PRI' THEN COLUMN_NAME END
                    ORDER BY ORDINAL_POSITION
                    SEPARATOR ', '
                ) AS PRIMARY_KEY_COLUMNS
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = '{source_database}'
            GROUP BY TABLE_SCHEMA, TABLE_NAME
            ORDER BY TABLE_SCHEMA, TABLE_NAME
            """

            df = query_execution(connection, "mysql", query)
            connection.close()

            return df

        if sourc_platform == "postgres":
            connection = get_Source_connection(config_path, sourc_platform)
            source_database = parse_config(config_path)["postgres"]["database"]

            query = f"""
            SELECT
                current_database() AS DB_NAME,
                t.table_schema AS TABLE_SCHEMA,
                t.table_name AS TABLE_NAME,
                STRING_AGG(kcu.column_name, ', ' ORDER BY kcu.ordinal_position) AS PRIMARY_KEY_COLUMNS
            FROM information_schema.tables t
            LEFT JOIN information_schema.table_constraints tc
                ON tc.table_catalog = t.table_catalog
               AND tc.table_schema = t.table_schema
               AND tc.table_name = t.table_name
               AND tc.constraint_type = 'PRIMARY KEY'
            LEFT JOIN information_schema.key_column_usage kcu
                ON kcu.constraint_catalog = tc.constraint_catalog
               AND kcu.constraint_schema = tc.constraint_schema
               AND kcu.constraint_name = tc.constraint_name
               AND kcu.table_schema = tc.table_schema
               AND kcu.table_name = tc.table_name
            WHERE t.table_type = 'BASE TABLE'
              AND t.table_catalog = '{source_database}'
              AND t.table_schema NOT IN ('pg_catalog', 'information_schema')
            GROUP BY t.table_schema, t.table_name
            ORDER BY t.table_schema, t.table_name
            """

            df = query_execution(connection, "postgres", query)
            connection.close()

            return df

        if sourc_platform == "oracle":
            connection = get_Source_connection(config_path, sourc_platform)
            oracle_cfg = parse_config(config_path)["oracle"]
            source_schema = oracle_cfg["schema"].upper()
            source_database = oracle_cfg["service_name"]

            query = f"""
            SELECT
                '{source_database}' AS DB_NAME,
                t.OWNER AS TABLE_SCHEMA,
                t.TABLE_NAME AS TABLE_NAME,
                LISTAGG(cc.COLUMN_NAME, ', ') WITHIN GROUP (ORDER BY cc.POSITION) AS PRIMARY_KEY_COLUMNS
            FROM ALL_TABLES t
            LEFT JOIN ALL_CONSTRAINTS c
                ON c.OWNER = t.OWNER
               AND c.TABLE_NAME = t.TABLE_NAME
               AND c.CONSTRAINT_TYPE = 'P'
            LEFT JOIN ALL_CONS_COLUMNS cc
                ON cc.OWNER = c.OWNER
               AND cc.CONSTRAINT_NAME = c.CONSTRAINT_NAME
               AND cc.TABLE_NAME = c.TABLE_NAME
            WHERE t.OWNER = '{source_schema}'
            GROUP BY t.OWNER, t.TABLE_NAME
            ORDER BY t.OWNER, t.TABLE_NAME
            """

            df = query_execution(connection, "oracle", query)
            connection.close()

            return df

        if sourc_platform == "teradata":
            connection = get_Source_connection(config_path, sourc_platform)
            teradata_cfg = parse_config(config_path)["teradata"]
            source_database = teradata_cfg["database"]

            query = f"""
            SELECT
                t.DatabaseName AS DB_NAME,
                t.DatabaseName AS TABLE_SCHEMA,
                t.TableName AS TABLE_NAME,
                TRIM(TRAILING ',' FROM TRIM(TRAILING ' ' FROM (CAST(XMLAGG(TRIM(i.ColumnName) || ', ' ORDER BY i.ColumnPosition) AS VARCHAR(1000))))) AS PRIMARY_KEY_COLUMNS
            FROM DBC.TablesV t
            LEFT JOIN DBC.IndicesV i
                ON t.DatabaseName = i.DatabaseName
               AND t.TableName = i.TableName
               AND i.IndexType IN ('P', 'K')
            WHERE t.DatabaseName = '{source_database}'
              AND t.TableKind = 'T'
            GROUP BY t.DatabaseName, t.TableName
            ORDER BY t.TableName
            """

            df = query_execution(connection, "teradata", query)
            connection.close()

            return df

        # Return None for unsupported platforms
        return None

    except Exception as e:
        logger.info(f"Error retrieving source metadata: {str(e)}")
        raise Exception(f"Error retrieving source metadata: {str(e)}")
