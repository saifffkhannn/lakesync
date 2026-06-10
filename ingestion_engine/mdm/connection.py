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
            database = creds.get("database", "").strip()
            schema = creds.get("schema", "PUBLIC").strip()

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
