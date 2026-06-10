import pyodbc
from src.config_parser import parse_config
from databricks import sql
import configparser
from src.pipeline_logger import get_logger
import snowflake.connector
from google.cloud import bigquery

# Initialize logger
logger = get_logger()


def get_snowflake_stage_schema(database: str) -> str:
    """Returns staging schema name: cloud_stage."""
    return "cloud_stage"



# MySQL and Oracle connectors — imported lazily to avoid hard dependency failures
def _get_mysql_connector():
    try:
        import mysql.connector
        return mysql.connector
    except ImportError:
        raise ImportError("mysql-connector-python is not installed. Run: pip install mysql-connector-python")


def _get_oracle_lib():
    try:
        import oracledb
        return oracledb
    except ImportError:
        pass
    try:
        import cx_Oracle  # type: ignore
        return cx_Oracle
    except ImportError:
        raise ImportError("oracledb or cx_Oracle is not installed. Run: pip install oracledb")


def _get_teradata_connector():
    try:
        import teradatasql  # type: ignore
        return teradatasql
    except ImportError:
        raise ImportError("teradatasql is not installed. Run: pip install teradatasql")


# -------------------------------------------------------------------
# TERADATA CONNECTION
# -------------------------------------------------------------------

def teradata_connection(config_path):
    """
    Creates a connection to Teradata using credentials from config.

    Returns:
        teradatasql.connect connection
    """
    try:
        config = configparser.ConfigParser()
        config.read(config_path)

        tc = config["teradata"]
        lib = _get_teradata_connector()

        host = tc["host"]
        user = tc["user"]
        password = tc["password"]
        database = tc.get("database", "").strip()

        logger.info("Connecting to Teradata...")
        print("Connecting to Teradata...")

        conn = lib.connect(host=host, user=user, password=password)

        if database:
            cursor = conn.cursor()
            cursor.execute(f"DATABASE {database};")
            cursor.close()

        logger.info("Connected to Teradata.")
        print("Connected to Teradata.")
        return conn

    except KeyError as e:
        logger.info(f"Missing Teradata config key: {e}")
        raise KeyError(f"Missing Teradata config key: {e}")

    except Exception as e:
        logger.info(f"Teradata connection failed: {str(e)}")
        raise Exception(f"Teradata connection failed: {str(e)}")


# -------------------------------------------------------------------
# SAP SAPSQLSERVER CONNECTION
# -------------------------------------------------------------------

def sap_sapsqlserver_connection(config_path):
    """
    Creates a connection to SAP SQL Server using credentials from config.

    Flow:
    1. Parse config file
    2. Extract required credentials
    3. Build ODBC connection string
    4. Establish connection

    Returns:
        pyodbc.Connection
    """

    try:
        # Load configuration
        parsed_config = parse_config(filename=config_path)

        # Retrieve SQL Server credentials
        sql_config = parsed_config["sapsqlserver"]

        server = sql_config["server_name"]
        user = sql_config["user"]
        password = sql_config["password"]
        database = sql_config["database"]
        port = sql_config.get("port", "1433")  # Default port if not provided

        # Build ODBC connection string
        conn_str = (
            f"DRIVER={{ODBC Driver 17 for SQL Server}};"
            f"SERVER={server},{port};"
            f"DATABASE={database};"
            f"UID={user};"
            f"PWD={password};"
            f"Encrypt=no;"
            f"TrustServerCertificate=yes;"
        )

        logger.info("Connecting to SAP SQL Server...")
        print("Connecting to SAP SQL Server...")

        # Create connection
        conn = pyodbc.connect(conn_str)

        if conn:
            logger.info("Connected to SAP SQL Server.")
            print("Connected to SAP SQL Server.")

        return conn

    except KeyError as e:
        # Missing required config key
        logger.info(f"Missing SQL Server config key: {e}")
        raise KeyError(f"Missing SQL Server config key: {e}")

    except pyodbc.InterfaceError as e:
        # Driver / DSN related issues
        logger.info(f"ODBC Interface error: {str(e)}")
        raise Exception(f"ODBC Interface error: {str(e)}")

    except pyodbc.OperationalError as e:
        # Network / authentication issues
        logger.info(f"Operational error (connection/auth issue): {str(e)}")
        raise Exception(f"Operational error: {str(e)}")

    except pyodbc.Error as e:
        # Generic SQL Server error
        logger.info(f"SQL Server connection failed: {str(e)}")
        raise Exception(f"SQL Server connection failed: {str(e)}")

    except Exception as e:
        # Catch-all unexpected errors
        logger.info(f"Unexpected error connecting to SQL Server: {str(e)}")
        raise Exception(f"Unexpected error connecting to SQL Server: {str(e)}")


# -------------------------------------------------------------------
# MYSQL CONNECTION
# -------------------------------------------------------------------

def mysql_connection(config_path):
    """
    Creates a connection to MySQL using credentials from config.

    Returns:
        mysql.connector.connection
    """
    try:
        config = configparser.ConfigParser()
        config.read(config_path)

        mc = config["mysql"]
        mysql_lib = _get_mysql_connector()

        conn = mysql_lib.connect(
            host=mc["host"],
            port=int(mc.get("port", "3306")),
            database=mc["database"],
            user=mc["user"],
            password=mc["password"],
            connection_timeout=30
        )

        logger.info("Connected to MySQL.")
        print("Connected to MySQL.")
        return conn

    except KeyError as e:
        logger.info(f"Missing MySQL config key: {e}")
        raise KeyError(f"Missing MySQL config key: {e}")

    except Exception as e:
        logger.info(f"MySQL connection failed: {str(e)}")
        raise Exception(f"MySQL connection failed: {str(e)}")


# -------------------------------------------------------------------
# ORACLE CONNECTION
# -------------------------------------------------------------------

def oracle_connection(config_path):
    """
    Creates a connection to Oracle using credentials from config.

    Returns:
        oracledb / cx_Oracle connection
    """
    try:
        config = configparser.ConfigParser()
        config.read(config_path)

        oc = config["oracle"]
        lib = _get_oracle_lib()

        host = oc["host"]
        port = oc.get("port", "1521")
        service_name = oc["service_name"]
        dsn = f"{host}:{port}/{service_name}"

        conn = lib.connect(user=oc["user"], password=oc["password"], dsn=dsn)

        logger.info("Connected to Oracle.")
        print("Connected to Oracle.")
        return conn

    except KeyError as e:
        logger.info(f"Missing Oracle config key: {e}")
        raise KeyError(f"Missing Oracle config key: {e}")

    except Exception as e:
        logger.info(f"Oracle connection failed: {str(e)}")
        raise Exception(f"Oracle connection failed: {str(e)}")


# -------------------------------------------------------------------
# DATABRICKS CONNECTION
# -------------------------------------------------------------------

def databricks_connection(config_path):
    """
    Creates a connection to Databricks SQL warehouse.

    Flow:
    1. Read config file
    2. Extract credentials
    3. Establish connection

    Returns:
        databricks.sql.Connection
    """

    try:
        config = configparser.ConfigParser()
        config.read(config_path)

        # Reading connection credentials
        server_hostname = config["databricks"]["server_hostname"]
        http_path = config["databricks"]["http_path"]
        access_token = config["databricks"]["access_token"]

        # Establish connection
        conn = sql.connect(
            server_hostname=server_hostname,
            http_path=http_path,
            access_token=access_token,
            catalog=config["databricks"].get("catalog")
        )

        logger.info("Connected to databricks")
        print("Connected to databricks")

        return conn

    except KeyError as e:
        # Missing config keys
        logger.info(f"Missing Databricks config key: {e}")
        raise KeyError(f"Missing Databricks config key: {e}")

    except ValueError as e:
        # Invalid values in config
        logger.info(f"Invalid Databricks configuration: {str(e)}")
        raise Exception(f"Invalid Databricks configuration: {str(e)}")

    except Exception as e:
        # General failure
        logger.info(f"Failed to connect to Databricks: {str(e)}")
        raise Exception(f"Failed to connect to Databricks: {str(e)}")


# -------------------------------------------------------------------
# SNOWFLAKE CONNECTION
# -------------------------------------------------------------------

def snowflake_connection(config_path):
    """
    Creates a connection to Snowflake.

    Flow:
    1. Read config
    2. Extract credentials
    3. Establish connection

    Returns:
        snowflake.connector.connection
    """

    try:
        config = configparser.ConfigParser()
        config.read(config_path)

        sf = config["snowflake"]

        # Extract and sanitize values
        account = sf["account"].strip()
        user = sf["user"].strip()
        password = sf["password"].strip()
        warehouse = sf["warehouse"].strip()
        database = sf["database"].strip()
        schema = (sf.get("stage_schema", "") or sf.get("stage_name", "")).strip() or f"{database}_stg"

        # Establish connection
        conn = snowflake.connector.connect(
            account=account,
            user=user,
            password=password,
            warehouse=warehouse,
            database=database,
            schema=schema
        )

        logger.info("Connected to Snowflake")
        return conn

    except KeyError as e:
        logger.info(f"Missing Snowflake config key: {e}")
        raise KeyError(f"Missing Snowflake config key: {e}")

    except snowflake.connector.errors.DatabaseError as e:
        # Issues like invalid warehouse/db/schema
        logger.info(f"Snowflake database error: {str(e)}")
        raise Exception(f"Snowflake database error: {str(e)}")

    except snowflake.connector.errors.InterfaceError as e:
        # Connection-level issues
        logger.info(f"Snowflake interface error: {str(e)}")
        raise Exception(f"Snowflake interface error: {str(e)}")

    except Exception as e:
        logger.info(f"Failed to connect to Snowflake: {str(e)}")
        raise Exception(f"Failed to connect to Snowflake: {str(e)}")


# -------------------------------------------------------------------
# BIG QUERY CONNECTION
# -------------------------------------------------------------------

def bigquery_connection(config_path):
    """
    Creates a connection to BigQuery.

    Flow:
    1. Parse config
    2. Load service account
    3. Create client

    Returns:
        google.cloud.bigquery.Client
    """

    try:
        config = parse_config(config_path)
        bq_cfg = config["bigquery"]

        # Initialize BigQuery client
        client = bigquery.Client.from_service_account_json(
            bq_cfg["service_account_json"],
            project=bq_cfg["project"]
        )

        logger.info("Connected to BigQuery")
        return client

    except KeyError as e:
        logger.info(f"Missing BigQuery config key: {e}")
        raise KeyError(f"Missing BigQuery config key: {e}")

    except FileNotFoundError as e:
        # Service account JSON path issue
        logger.info(f"Service account file not found: {str(e)}")
        raise Exception(f"Service account file not found: {str(e)}")

    except Exception as e:
        logger.info(f"Failed to connect to BigQuery: {str(e)}")
        raise Exception(f"Failed to connect to BigQuery: {str(e)}")


def sqlserver_connection(config_path):
    try:
        parsed_config = parse_config(filename=config_path)
        sql_config = parsed_config["sqlserver"]

        server = sql_config["server_name"]
        user = sql_config["user"]
        password = sql_config["password"]
        database = sql_config["database"]
        port = sql_config.get("port", "1433")

        conn_str = (
            f"DRIVER={{ODBC Driver 17 for SQL Server}};"
            f"SERVER={server},{port};"
            f"DATABASE={database};"
            f"UID={user};"
            f"PWD={password};"
            f"TrustServerCertificate=yes;"
        )

        logger.info("Connecting to SQL Server...")
        conn = pyodbc.connect(conn_str)

        if conn:
            logger.info("Connected to SQL Server.")

        return conn

    except KeyError as e:
        logger.info(f"Missing SQL Server config key: {e}")
        raise KeyError(f"Missing SQL Server config key: {e}")

    except pyodbc.Error as e:
        logger.info(f"SQL Server connection failed: {str(e)}")
        raise Exception(f"SQL Server connection failed: {str(e)}")

    except Exception as e:
        logger.info(f"Unexpected error connecting to SQL Server: {str(e)}")
        raise Exception(f"Unexpected error connecting to SQL Server: {str(e)}")


def postgres_connection(config_path):
    try:
        import psycopg2

        parsed_config = parse_config(filename=config_path)
        pg_config = parsed_config["postgres"]

        host = pg_config["host"]
        user = pg_config["user"]
        password = pg_config["password"]
        database = pg_config["database"]
        port = int(pg_config.get("port", "5432"))

        logger.info("Connecting to PostgreSQL...")

        conn = psycopg2.connect(
            host=host,
            user=user,
            password=password,
            dbname=database,
            port=port
        )

        if conn:
            logger.info("Connected to PostgreSQL.")

        return conn

    except KeyError as e:
        logger.info(f"Missing PostgreSQL config key: {e}")
        raise KeyError(f"Missing PostgreSQL config key: {e}")

    except ModuleNotFoundError:
        logger.info("psycopg2 is not installed")
        raise Exception("psycopg2 is not installed. Install it with: pip install psycopg2-binary")

    except psycopg2.Error as e:
        logger.info(f"PostgreSQL connection failed: {str(e)}")
        raise Exception(f"PostgreSQL connection failed: {str(e)}")

    except Exception as e:
        logger.info(f"Unexpected error connecting to PostgreSQL: {str(e)}")
        raise Exception(f"Unexpected error connecting to PostgreSQL: {str(e)}")


def get_Source_connection(config_path, source_type):
    """
    Returns connection object for the specified source system.

    Supported:
    - sapsqlserver
    - sqlserver
    - mysql
    - postgres
    - oracle
    - teradata
    """

    try:
        if source_type == "sapsqlserver":
            return sap_sapsqlserver_connection(config_path)

        elif source_type == "sqlserver":
            return sqlserver_connection(config_path)

        elif source_type == "mysql":
            return mysql_connection(config_path)

        elif source_type == "postgres":
            return postgres_connection(config_path)

        elif source_type == "oracle":
            return oracle_connection(config_path)

        elif source_type == "teradata":
            return teradata_connection(config_path)

        else:
            logger.info(f"Unsupported source type: {source_type}")
            raise ValueError(f"Unsupported source type: {source_type}")

    except Exception as e:
        logger.info(f"Error creating source connection: {str(e)}")
        raise Exception(f"Error creating source connection: {str(e)}")


def get_Target_connection(config_path, Target_type):
    """
    Returns connection object for the specified target system.

    Supported:
    - databricks
    - snowflake
    - bigquery
    """

    try:
        if Target_type == "databricks":
            return databricks_connection(config_path)

        elif Target_type == "snowflake":
            return snowflake_connection(config_path)

        elif Target_type == "bigquery":
            return bigquery_connection(config_path)

        else:
            logger.info(f"Unsupported target type: {Target_type}")
            raise ValueError(f"Unsupported target type: {Target_type}")

    except Exception as e:
        logger.info(f"Error creating target connection: {str(e)}")
        raise Exception(f"Error creating target connection: {str(e)}")
