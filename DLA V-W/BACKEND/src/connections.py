import pyodbc
from src.parse_config import parse_config
from databricks import sql
import configparser
from src.custom_logger import get_logger
import snowflake.connector
from google.cloud import bigquery
 
# Initialize logger
logger = get_logger()


def get_snowflake_stage_schema(database: str) -> str:
    return f"{database}_STG"

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


def sqlserver_connection(config_path):
    """
    Creates a connection to SQL Server using credentials from config.
    """

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


def mysql_connection(config_path):
    """
    Creates a connection to MySQL using credentials from config.

    Returns:
        pymysql.connections.Connection
    """

    try:
        import pymysql

        parsed_config = parse_config(filename=config_path)
        mysql_config = parsed_config["mysql"]

        host = mysql_config["host"]
        user = mysql_config["user"]
        password = mysql_config["password"]
        database = mysql_config["database"]
        port = int(mysql_config.get("port", "3306"))

        logger.info("Connecting to MySQL...")

        conn = pymysql.connect(
            host=host,
            user=user,
            password=password,
            database=database,
            port=port,
            cursorclass=pymysql.cursors.Cursor
        )

        if conn:
            logger.info("Connected to MySQL.")

        return conn

    except KeyError as e:
        logger.info(f"Missing MySQL config key: {e}")
        raise KeyError(f"Missing MySQL config key: {e}")

    except ModuleNotFoundError:
        logger.info("PyMySQL is not installed")
        raise Exception("PyMySQL is not installed. Install it with: pip install pymysql")

    except pymysql.MySQLError as e:
        logger.info(f"MySQL connection failed: {str(e)}")
        raise Exception(f"MySQL connection failed: {str(e)}")

    except Exception as e:
        logger.info(f"Unexpected error connecting to MySQL: {str(e)}")
        raise Exception(f"Unexpected error connecting to MySQL: {str(e)}")


def postgres_connection(config_path):
    """
    Creates a connection to PostgreSQL using credentials from config.
    """

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


def oracle_connection(config_path):
    """
    Creates a connection to Oracle using credentials from config.
    """

    try:
        import oracledb

        parsed_config = parse_config(filename=config_path)
        oracle_config = parsed_config["oracle"]

        host = oracle_config["host"]
        user = oracle_config["user"]
        password = oracle_config["password"]
        service_name = oracle_config["service_name"]
        port = int(oracle_config.get("port", "1521"))

        dsn = oracledb.makedsn(host, port, service_name=service_name)

        logger.info("Connecting to Oracle...")

        conn = oracledb.connect(
            user=user,
            password=password,
            dsn=dsn
        )

        if conn:
            logger.info("Connected to Oracle.")

        return conn

    except ModuleNotFoundError:
        logger.info("oracledb is not installed")
        raise Exception("oracledb is not installed. Install it with: pip install oracledb")

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
            access_token=access_token
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
        # Establish connection
        conn = snowflake.connector.connect(
            account=account,
            user=user,
            password=password,
            warehouse=warehouse,
            database=database
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
 
 

 
def get_Source_connection(config_path, source_type):
    """
    Returns connection object for the specified source system.
 
    Supported:
    - sapsqlserver
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
