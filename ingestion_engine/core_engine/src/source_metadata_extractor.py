import pandas as pd
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
            source_schema = oracle_cfg.get("schema", oracle_cfg.get("user", oracle_cfg.get("username", "SYSTEM"))).upper()
            source_database = oracle_cfg["service_name"]

            # Exclude system/internal schemas
            exclude_schemas = (
                'SYS', 'OUTLN', 'DBSNMP', 'APPQOSSYS', 'AUDSYS', 'CTXSYS', 
                'DBSFWUSER', 'DVSYS', 'GSMADMIN_INTERNAL', 'LBACSYS', 'MDSYS', 
                'OJVMSYS', 'OLAPSYS', 'ORDDATA', 'ORDSYS', 'WMSYS', 'XDB', 'XS$NULL',
                'ANONYMOUS', 'DGPDB_INT', 'DIP', 'DVF', 'GGSYS', 'GSMCATUSER', 'GSMUSER',
                'MDDATA', 'ORACLE_OCM', 'ORDPLUGINS', 'PDBADMIN', 'REMOTE_SCHEDULER_AGENT',
                'SI_INFORMTN_SCHEMA', 'SYS$UMF', 'SYSBACKUP', 'SYSDG', 'SYSKM', 'SYSRAC'
            )
            exclude_placeholder = ", ".join(f"'{s}'" for s in exclude_schemas)

            try:
                # Query tables and primary keys separately to prevent performance hang on Oracle's metadata views
                tables_query = f"""
                SELECT OWNER AS TABLE_SCHEMA, TABLE_NAME 
                FROM ALL_TABLES 
                WHERE OWNER NOT IN ({exclude_placeholder})
                ORDER BY OWNER, TABLE_NAME
                """
                df_tables = query_execution(connection, "oracle", tables_query)

                pk_query = f"""
                SELECT cols.OWNER AS TABLE_SCHEMA, cols.TABLE_NAME, cols.COLUMN_NAME
                FROM ALL_CONSTRAINTS cons
                JOIN ALL_CONS_COLUMNS cols 
                  ON cons.CONSTRAINT_NAME = cols.CONSTRAINT_NAME 
                 AND cons.OWNER = cols.OWNER
                WHERE cons.CONSTRAINT_TYPE = 'P'
                  AND cons.OWNER NOT IN ({exclude_placeholder})
                ORDER BY cols.OWNER, cols.TABLE_NAME, cols.POSITION
                """
                df_pks = query_execution(connection, "oracle", pk_query)

                # Group primary keys by schema and table
                pk_map = {}
                for _, row in df_pks.iterrows():
                    key = (row["TABLE_SCHEMA"], row["TABLE_NAME"])
                    if key not in pk_map:
                        pk_map[key] = []
                    pk_map[key].append(str(row["COLUMN_NAME"]))

                # Combine tables and primary keys
                results = []
                for _, row in df_tables.iterrows():
                    owner = row["TABLE_SCHEMA"]
                    table = row["TABLE_NAME"]
                    pk_cols = ", ".join(pk_map.get((owner, table), []))
                    results.append({
                        "DB_NAME": source_database,
                        "TABLE_SCHEMA": owner,
                        "TABLE_NAME": table,
                        "PRIMARY_KEY_COLUMNS": pk_cols if pk_cols else None
                    })

                df = pd.DataFrame(results)
                connection.close()
                return df
            except Exception as e:
                logger.info(f"Optimized Oracle metadata query failed: {str(e)}. Falling back to legacy query.")
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
                WHERE t.OWNER NOT IN ({exclude_placeholder})
                GROUP BY t.OWNER, t.TABLE_NAME
                ORDER BY t.OWNER, t.TABLE_NAME
                """
                df = query_execution(connection, "oracle", query)
                connection.close()
                return df

        # Return None for unsupported platforms
        return None

    except Exception as e:
        logger.info(f"Error retrieving source metadata: {str(e)}")
        raise Exception(f"Error retrieving source metadata: {str(e)}")
