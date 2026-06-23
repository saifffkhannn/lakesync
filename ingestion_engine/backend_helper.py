import os
import sys
import json
import configparser
import logging
import csv

# Add backend to path
BACKEND_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "core_engine")
if BACKEND_ROOT not in sys.path:
    sys.path.append(BACKEND_ROOT)

# Now we can import from src
from src.db_connections import get_Source_connection, get_Target_connection
from src.incremental_load_pipeline import incremental_load
logger = logging.getLogger("backend_helper")

class BackendHelper:
    def __init__(self, config_path_json):
        self.config_path_json = config_path_json
        self.config_dir = os.path.join(os.path.dirname(config_path_json))
        os.makedirs(self.config_dir, exist_ok=True)
        
    def _get_config_dict(self):
        if not os.path.exists(self.config_path_json):
            return {}
        with open(self.config_path_json, 'r') as f:
            return json.load(f)

    def create_temp_cfg(self, config_dict=None):
        """Creates a .cfg file that the backend connections.py expects."""
        if config_dict is None:
            config_dict = self._get_config_dict()
            
        config = configparser.ConfigParser(interpolation=None)
        
        # Source
        source_platform = config_dict.get("source", {}).get("platform", "sapsqlserver").lower()
        source_type = "sapsqlserver" if source_platform in ["sqlserver", "sapsqlserver"] else source_platform
        src_data = config_dict.get("source", {})
        if source_type == "sapsqlserver":
            config["sapsqlserver"] = {
                "server_name": src_data.get("server_name", src_data.get("server", "")),
                "user": src_data.get("user", src_data.get("username", "")),
                "password": src_data.get("password", ""),
                "database": src_data.get("database", ""),
                "port": str(src_data.get("port", "1433"))
            }
        elif source_type == "mysql":
            config["mysql"] = {
                "host": src_data.get("host", ""),
                "port": str(src_data.get("port", "3306")),
                "database": src_data.get("database", ""),
                "user": src_data.get("user", src_data.get("username", "")),
                "password": src_data.get("password", ""),
            }
        elif source_type == "oracle":
            config["oracle"] = {
                "host": src_data.get("host", ""),
                "port": str(src_data.get("port", "1521")),
                "service_name": src_data.get("service_name", ""),
                "user": src_data.get("user", src_data.get("username", "")),
                "password": src_data.get("password", ""),
            }
        elif source_type == "teradata":
            config["teradata"] = {
                "host": src_data.get("host", src_data.get("server_name", "")),
                "user": src_data.get("user", src_data.get("username", "")),
                "password": src_data.get("password", ""),
                "database": src_data.get("database", ""),
                "port": str(src_data.get("port", "1025"))
            }
        
        # Target
        target_type = config_dict.get("target", {}).get("platform", "Snowflake").lower()
        tgt_data = config_dict.get("target", {})
        if target_type == "snowflake":
            config["snowflake"] = {
                "account": tgt_data.get("account", ""),
                "user": tgt_data.get("user", tgt_data.get("username", "")),
                "password": tgt_data.get("password", ""),
                "warehouse": tgt_data.get("warehouse", ""),
                "database": tgt_data.get("database", "")
            }
        elif target_type == "databricks":
            config["databricks"] = {
                "server_hostname": tgt_data.get("server_hostname", ""),
                "http_path": tgt_data.get("http_path", ""),
                "access_token": tgt_data.get("access_token", ""),
                "catalog": tgt_data.get("catalog", tgt_data.get("database", ""))
            }
        elif target_type == "bigquery":
            config["bigquery"] = {
                "project": tgt_data.get("project", tgt_data.get("project_id", "")),
                "service_account_json": tgt_data.get("service_account_json", "")
            }

        # Cloud
        cloud_type = config_dict.get("cloud", {}).get("platform", "aws").lower()
        cloud_data = config_dict.get("cloud", {})
        config[cloud_type] = cloud_data

        # Pipeline
        config["pipeline"] = {
            "load_type": config_dict.get("load_type", "INCREMENTAL").upper()
        }

        cfg_name = f"{source_type}_{cloud_type}_{target_type}.cfg"
        cfg_path = os.path.join(BACKEND_ROOT, "config", cfg_name)
        os.makedirs(os.path.dirname(cfg_path), exist_ok=True)
        
        with open(cfg_path, 'w') as f:
            config.write(f)
        return cfg_path, source_type, target_type, cloud_type

    def get_source_metadata(self, schema_name=None, table_name=None, action="schemas"):
        config_dict = self._get_config_dict()
        cfg_path, source_type, _, _ = self.create_temp_cfg(config_dict)

        conn = get_Source_connection(cfg_path, source_type)
        try:
            cursor = conn.cursor()

            if source_type == "mysql":
                if action == "schemas":
                    cursor.execute("SELECT SCHEMA_NAME FROM information_schema.SCHEMATA WHERE SCHEMA_NAME NOT IN ('information_schema','performance_schema','mysql','sys')")
                    return [row[0] for row in cursor.fetchall()]
                elif action == "tables":
                    cursor.execute(f"SELECT TABLE_NAME FROM information_schema.TABLES WHERE TABLE_SCHEMA = '{schema_name}' AND TABLE_TYPE = 'BASE TABLE'")
                    return [row[0] for row in cursor.fetchall()]
                elif action == "columns":
                    cursor.execute(f"""
                        SELECT COLUMN_NAME, DATA_TYPE, CHARACTER_MAXIMUM_LENGTH,
                               NUMERIC_PRECISION, NUMERIC_SCALE, ORDINAL_POSITION, IS_NULLABLE
                        FROM information_schema.COLUMNS
                        WHERE TABLE_SCHEMA = '{schema_name}' AND TABLE_NAME = '{table_name}'
                        ORDER BY ORDINAL_POSITION
                    """)
                    rows = cursor.fetchall()
                    cursor.execute(f"""
                        SELECT COLUMN_NAME FROM information_schema.KEY_COLUMN_USAGE
                        WHERE TABLE_SCHEMA = '{schema_name}' AND TABLE_NAME = '{table_name}'
                        AND CONSTRAINT_NAME = 'PRIMARY'
                    """)
                    pks = [r[0] for r in cursor.fetchall()]
                    return [{
                        "column_name": row[0],
                        "data_type": str(row[1]).lower(),
                        "char_length": row[2],
                        "precision": row[3],
                        "scale": row[4],
                        "ordinal_position": row[5],
                        "nullable": row[6],
                        "is_primary_key": row[0] in pks
                    } for row in rows]

            elif source_type == "oracle":
                if action == "schemas":
                    exclude_schemas = (
                        'SYS', 'OUTLN', 'DBSNMP', 'APPQOSSYS', 'AUDSYS', 'CTXSYS', 
                        'DBSFWUSER', 'DVSYS', 'GSMADMIN_INTERNAL', 'LBACSYS', 'MDSYS', 
                        'OJVMSYS', 'OLAPSYS', 'ORDDATA', 'ORDSYS', 'WMSYS', 'XDB', 'XS$NULL',
                        'ANONYMOUS', 'DGPDB_INT', 'DIP', 'DVF', 'GGSYS', 'GSMCATUSER', 'GSMUSER',
                        'MDDATA', 'ORACLE_OCM', 'ORDPLUGINS', 'PDBADMIN', 'REMOTE_SCHEDULER_AGENT',
                        'SI_INFORMTN_SCHEMA', 'SYS$UMF', 'SYSBACKUP', 'SYSDG', 'SYSKM', 'SYSRAC'
                    )
                    cursor.execute("SELECT USERNAME FROM all_users ORDER BY USERNAME")
                    return [row[0] for row in cursor.fetchall() if row[0] not in exclude_schemas]
                elif action == "tables":
                    cursor.execute("SELECT TABLE_NAME FROM all_tables WHERE OWNER = :owner ORDER BY TABLE_NAME", {"owner": schema_name.upper()})
                    return [row[0] for row in cursor.fetchall()]
                elif action == "columns":
                    cursor.execute("""
                        SELECT COLUMN_NAME, DATA_TYPE, CHAR_COL_DECL_LENGTH,
                                DATA_PRECISION, DATA_SCALE, COLUMN_ID,
                                CASE WHEN NULLABLE = 'Y' THEN 'YES' ELSE 'NO' END AS IS_NULLABLE
                        FROM all_tab_columns
                        WHERE OWNER = :owner AND TABLE_NAME = :tbl
                        ORDER BY COLUMN_ID
                    """, {"owner": schema_name.upper(), "tbl": table_name.upper()})
                    rows = cursor.fetchall()
                    cursor.execute("""
                        SELECT cols.COLUMN_NAME
                        FROM all_constraints cons
                        JOIN all_cons_columns cols
                            ON cons.CONSTRAINT_NAME = cols.CONSTRAINT_NAME AND cons.OWNER = cols.OWNER
                        WHERE cons.CONSTRAINT_TYPE = 'P'
                        AND cons.OWNER = :owner AND cons.TABLE_NAME = :tbl
                    """, {"owner": schema_name.upper(), "tbl": table_name.upper()})
                    pks = [r[0] for r in cursor.fetchall()]
                    return [{
                        "column_name": row[0],
                        "data_type": str(row[1]).lower(),
                        "char_length": row[2],
                        "precision": row[3],
                        "scale": row[4],
                        "ordinal_position": row[5],
                        "nullable": row[6],
                        "is_primary_key": row[0] in pks
                    } for row in rows]

            elif source_type == "teradata":
                if action == "schemas":
                    cursor.execute("SELECT DatabaseName FROM DBC.DatabasesV ORDER BY DatabaseName")
                    return [row[0] for row in cursor.fetchall()]
                elif action == "tables":
                    cursor.execute(f"SELECT TableName FROM DBC.TablesV WHERE DatabaseName = '{schema_name}' AND TableKind = 'T' ORDER BY TableName")
                    return [row[0] for row in cursor.fetchall()]
                elif action == "columns":
                    cursor.execute(f"""
                        SELECT TRIM(ColumnName) 
                        FROM DBC.IndicesV 
                        WHERE DatabaseName = '{schema_name}' AND TableName = '{table_name}' AND IndexType IN ('P', 'K')
                    """)
                    pks = [str(row[0]).strip().lower() for row in cursor.fetchall()]

                    cursor.execute(f"""
                        SELECT TRIM(ColumnName), ColumnType, ColumnLength, DecimalFractionalDigits, ColumnId, Nullable
                        FROM DBC.ColumnsV
                        WHERE DatabaseName = '{schema_name}' AND TableName = '{table_name}'
                        ORDER BY ColumnId
                    """)
                    rows = cursor.fetchall()
                    
                    type_mapping = {
                        'BF': 'byte', 'BV': 'varbyte', 'CF': 'char', 'CV': 'varchar',
                        'D': 'decimal', 'DA': 'date', 'F': 'float', 'I1': 'byteint',
                        'I2': 'smallint', 'I8': 'bigint', 'I': 'integer', 'N': 'number',
                        'SZ': 'timestamp with time zone', 'TS': 'timestamp',
                        'TZ': 'time with time zone', 'TM': 'time', 'BO': 'blob', 'CO': 'clob'
                    }
                    
                    return [{
                        "column_name": str(row[0]).strip(),
                        "data_type": type_mapping.get(str(row[1]).strip().upper(), str(row[1]).lower()),
                        "char_length": row[2],
                        "precision": row[2] if str(row[1]).strip().upper() == 'D' else None,
                        "scale": row[3] if str(row[1]).strip().upper() == 'D' else None,
                        "ordinal_position": row[4],
                        "nullable": "YES" if str(row[5]).strip().upper() == 'Y' else "NO",
                        "is_primary_key": str(row[0]).strip().lower() in pks
                    } for row in rows]

            else:
                # Default: sapsqlserver
                if action == "schemas":
                    cursor.execute("SELECT name FROM sys.schemas")
                    return [row[0] for row in cursor.fetchall()]
                elif action == "tables":
                    cursor.execute(f"SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_SCHEMA = '{schema_name}' AND TABLE_TYPE = 'BASE TABLE'")
                    return [row[0] for row in cursor.fetchall()]
                elif action == "columns":
                    # PKs
                    pk_query = f"""
                    SELECT kcu.COLUMN_NAME
                    FROM INFORMATION_SCHEMA.TABLE_CONSTRAINTS tc 
                    JOIN INFORMATION_SCHEMA.KEY_COLUMN_USAGE kcu 
                        ON tc.CONSTRAINT_NAME = kcu.CONSTRAINT_NAME AND tc.TABLE_SCHEMA = kcu.TABLE_SCHEMA AND tc.TABLE_NAME = kcu.TABLE_NAME
                    WHERE tc.TABLE_SCHEMA = '{schema_name}'
                    AND tc.TABLE_NAME = '{table_name}' 
                    AND tc.CONSTRAINT_TYPE = 'PRIMARY KEY'
                    """
                    cursor.execute(pk_query)
                    pks = [row[0] for row in cursor.fetchall()]

                    query = f"""
                    SELECT COLUMN_NAME, DATA_TYPE, CHARACTER_MAXIMUM_LENGTH, NUMERIC_PRECISION, NUMERIC_SCALE, ORDINAL_POSITION, IS_NULLABLE
                    FROM INFORMATION_SCHEMA.COLUMNS
                    WHERE TABLE_SCHEMA = '{schema_name}' AND TABLE_NAME = '{table_name}'
                    ORDER BY ORDINAL_POSITION
                    """
                    cursor.execute(query)
                    rows = cursor.fetchall()
                    return [{
                        "column_name": row[0],
                        "data_type": row[1].lower(),
                        "char_length": row[2],
                        "precision": row[3],
                        "scale": row[4],
                        "ordinal_position": row[5],
                        "nullable": row[6],
                        "is_primary_key": row[0] in pks
                    } for row in rows]
        finally:
            if hasattr(conn, 'close'):
                conn.close()

    def get_target_metadata(self, schema_name=None, table_name=None, action="schemas"):
        config_dict = self._get_config_dict()
        cfg_path, _, target_type, _ = self.create_temp_cfg(config_dict)
        
        conn = get_Target_connection(cfg_path, target_type)
        try:
            if target_type == "snowflake":
                cursor = conn.cursor()
                # Use the database name exactly as configured (Snowflake is case-insensitive for unquoted identifiers)
                db_raw = config_dict["target"].get("database", "")
                db = db_raw.upper()  # Snowflake INFORMATION_SCHEMA uses uppercase names
                if action == "schemas":
                    try:
                        cursor.execute(f"SELECT SCHEMA_NAME FROM {db}.INFORMATION_SCHEMA.SCHEMATA WHERE SCHEMA_NAME <> 'INFORMATION_SCHEMA'")
                        return [row[0] for row in cursor.fetchall()]
                    except Exception as e:
                        err_str = str(e).lower()
                        if "does not exist" in err_str or "not authorized" in err_str:
                            # Target database may not exist yet (first Full Load creates it)
                            logger.warning(f"Target database '{db}' not found in Snowflake — returning empty schema list. It will be created by the pipeline.")
                            return []
                        raise
                elif action == "tables":
                    try:
                        cursor.execute(f"SELECT TABLE_NAME FROM {db}.INFORMATION_SCHEMA.TABLES WHERE TABLE_SCHEMA = '{schema_name.upper()}'")
                        return [row[0] for row in cursor.fetchall()]
                    except Exception as e:
                        if "does not exist" in str(e).lower() or "not authorized" in str(e).lower():
                            return []
                        raise
                elif action == "columns":
                    try:
                        cursor.execute(f"""
                            SELECT COLUMN_NAME, DATA_TYPE, CHARACTER_MAXIMUM_LENGTH, NUMERIC_PRECISION, NUMERIC_SCALE, ORDINAL_POSITION, IS_NULLABLE
                            FROM {db}.INFORMATION_SCHEMA.COLUMNS
                            WHERE TABLE_SCHEMA = '{schema_name.upper()}' AND TABLE_NAME = '{table_name.upper()}'
                            ORDER BY ORDINAL_POSITION
                        """)
                        rows = cursor.fetchall()
                        return [{
                            "column_name": row[0],
                            "data_type": row[1].lower() if row[1] else "",
                            "char_length": row[2],
                            "precision": row[3],
                            "scale": row[4],
                            "ordinal_position": row[5],
                            "nullable": row[6]
                        } for row in rows]
                    except Exception as e:
                        if "does not exist" in str(e).lower() or "not authorized" in str(e).lower() or "not found" in str(e).lower():
                            return []
                        raise
            
            elif target_type == "databricks":
                cursor = conn.cursor()
                catalog = config_dict["target"].get("catalog", config_dict["target"].get("database", ""))
                if action == "schemas":
                    if catalog:
                        try:
                            cursor.execute(f"USE CATALOG {catalog}")
                        except Exception as e:
                            logger.warning(f"Failed to use catalog {catalog}: {str(e)}")
                            if catalog and catalog.islower():
                                try:
                                    cursor.execute(f"USE CATALOG {catalog.upper()}")
                                    catalog = catalog.upper()
                                except: pass
                    cursor.execute("SHOW SCHEMAS")
                    return [row[0] for row in cursor.fetchall()]
                elif action == "tables":
                    prefix = f"{catalog}." if catalog else ""
                    cursor.execute(f"SHOW TABLES IN {prefix}{schema_name}")
                    return [row[1] for row in cursor.fetchall()]
                elif action == "columns":
                    try:
                        prefix = f"{catalog}." if catalog else ""
                        cursor.execute(f"""
                            SELECT COLUMN_NAME, DATA_TYPE, CHARACTER_MAXIMUM_LENGTH, NUMERIC_PRECISION, NUMERIC_SCALE, ORDINAL_POSITION, IS_NULLABLE
                            FROM {prefix}INFORMATION_SCHEMA.COLUMNS
                            WHERE TABLE_SCHEMA = '{schema_name}' AND TABLE_NAME = '{table_name}'
                            ORDER BY ORDINAL_POSITION
                        """)
                        rows = cursor.fetchall()
                        return [{
                            "column_name": row[0],
                            "data_type": row[1],
                            "char_length": row[2],
                            "precision": row[3],
                            "scale": row[4],
                            "ordinal_position": row[5],
                            "nullable": row[6]
                        } for row in rows]
                    except Exception as e:
                        if "does not exist" in str(e).lower() or "not authorized" in str(e).lower() or "not found" in str(e).lower():
                            return []
                        raise

            elif target_type == "bigquery":
                project = config_dict["target"].get("project_id")
                if action == "schemas":
                    return [ds.dataset_id for ds in conn.list_datasets(project)]
                elif action == "tables":
                    return [t.table_id for t in conn.list_tables(f"{project}.{schema_name}")]
                elif action == "columns":
                    try:
                        query = f"""
                            SELECT column_name, data_type, ordinal_position, is_nullable, column_default, is_generated
                            FROM `{project}.{schema_name}.INFORMATION_SCHEMA.COLUMNS`
                            WHERE table_name = '{table_name}'
                            ORDER BY ordinal_position
                        """
                        rows = conn.query(query).result()
                        return [{
                            "column_name": row.column_name,
                            "data_type": row.data_type.lower() if row.data_type else "",
                            "ordinal_position": row.ordinal_position,
                            "nullable": row.is_nullable,
                            "is_primary_key": False
                        } for row in rows]
                    except Exception as e:
                        if "not found" in str(e).lower() or "does not exist" in str(e).lower() or "not authorized" in str(e).lower():
                            return []
                        raise
        finally:
            if hasattr(conn, 'close'):
                conn.close()

    def save_mapping_to_backend(self, mappings):
        """Saves mappings to the backend's metadata CSV file."""
        config_dict = self._get_config_dict()
        source = config_dict.get("source", {}).get("platform", "sapsqlserver").lower()
        
        metadata_path = os.path.join(BACKEND_ROOT, "metadata", f"{source}_metadata.csv")
        os.makedirs(os.path.dirname(metadata_path), exist_ok=True)
        
        headers = [
            "SOURCE", "source_database", "source_schema", "source_table",
            "target", "target_database", "target_schema", "target_table",
            "Primary_key_column", "source selected columns", "target columns",
            "mapped_columns", "watermark column(src)"
        ]
        
        with open(metadata_path, "w", newline='') as f:
            writer = csv.writer(f)
            writer.writerow(headers)
            for m in mappings:
                formatted_map = {}
                for t_col, s_col in m.column_map.items():
                    val_str = str(s_col)
                    if val_str.upper() in {"NULL", "DEFAULT"}:
                        formatted_map[t_col] = val_str.upper()
                    elif val_str in m.source_columns:
                        formatted_map[t_col] = val_str
                    else:
                        if not val_str.lower().startswith(("literal:", "int:", "float:", "bool:")) and str(val_str).lower() not in {"now()", "timestamp:now", "datetime:now"}:
                            formatted_map[t_col] = f"literal:{val_str}"
                        else:
                            formatted_map[t_col] = val_str

                writer.writerow([
                    source,
                    m.src_db,
                    m.src_schema,
                    m.src_table,
                    config_dict.get("target", {}).get("platform", "snowflake").lower(),
                    m.tgt_db,
                    m.tgt_schema,
                    m.tgt_table,
                    json.dumps(m.primary_keys),
                    json.dumps(m.source_columns),
                    json.dumps(m.target_columns),
                    json.dumps(formatted_map),
                    m.incremental_src_col
                ])
        return metadata_path

    def run_pipeline(self):
        config_dict = self._get_config_dict()
        cfg_path, source, target, cloud = self.create_temp_cfg(config_dict)
        
        # Trigger the backend pipeline
        incremental_load(source, cloud, target)
