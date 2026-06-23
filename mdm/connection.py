import logging
import snowflake.connector

logger = logging.getLogger("mdm.connection")

class ConnectionManager:
    @staticmethod
    def get_connection(creds: dict):
        try:
            account = creds.get("account", "").strip()
            user = creds.get("username", creds.get("user", "")).strip()
            password = creds.get("password", "").strip()
            warehouse = creds.get("warehouse", "").strip()
            database_val = creds.get("database")
            database = database_val.strip() if database_val else None
            schema_val = creds.get("schema")
            schema = schema_val.strip() if schema_val else None

            return snowflake.connector.connect(
                account=account,
                user=user,
                password=password,
                warehouse=warehouse,
                database=database,
                schema=schema
            )
        except Exception as e:
            logger.error(f"MDM Snowflake connection failed: {e}")
            raise Exception(f"Failed to connect to Snowflake: {e}")
