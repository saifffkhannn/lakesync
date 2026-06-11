"""Snowflake database connector and storage bootstrap utilities."""

from collections.abc import Iterable
from contextlib import contextmanager
import os
from typing import Any

from app.core.config import Settings


class SnowflakeConfigurationError(RuntimeError):
    """Raised when Snowflake credentials or connector packages are unavailable."""

    pass


class SnowflakeConnector:
    """Thin wrapper around the Snowflake Python connector used by services."""

    def __init__(self, settings: Settings):
        """Store the typed settings used to open Snowflake sessions."""
        self.settings = settings
        self._active_connection = None

    def _connection_kwargs(self) -> dict[str, Any]:
        """Build connector keyword arguments and fail fast on missing credentials."""
        missing = [
            name
            for name, value in {
                "SNOWFLAKE_ACCOUNT": self.settings.snowflake_account,
                "SNOWFLAKE_USER": self.settings.snowflake_user,
                "SNOWFLAKE_PASSWORD": self.settings.snowflake_password,
                "SNOWFLAKE_WAREHOUSE": self.settings.snowflake_warehouse,
                "SNOWFLAKE_DATABASE": self.settings.snowflake_database,
                "SNOWFLAKE_SCHEMA": self.settings.snowflake_schema,
            }.items()
            if value is None
        ]
        if missing:
            raise SnowflakeConfigurationError(f"Missing Snowflake environment variables: {', '.join(missing)}")
        kwargs = {
            "account": self.settings.snowflake_account,
            "user": self.settings.snowflake_user,
            "password": self.settings.snowflake_password.get_secret_value()
            if self.settings.snowflake_password
            else None,
            "warehouse": self.settings.snowflake_warehouse,
            "database": self.settings.snowflake_database,
            "schema": self.settings.snowflake_schema,
            "client_session_keep_alive": False,
            "login_timeout": 15,
            "network_timeout": 45,
        }
        if self.settings.snowflake_role:
            kwargs["role"] = self.settings.snowflake_role
        return kwargs

    @contextmanager
    def connect(self):
        """Open a Snowflake connection and close it after the caller finishes."""
        try:
            import snowflake.connector
        except ImportError as exc:
            raise SnowflakeConfigurationError("Install snowflake-connector-python to use Snowflake") from exc

        with self._snowflake_proxy_context():
            connection = snowflake.connector.connect(**self._connection_kwargs())
            try:
                yield connection
            finally:
                connection.close()

    @contextmanager
    def session(self):
        """Reuse one Snowflake connection across a batch of related operations."""
        if self._active_connection is not None:
            yield
            return

        with self.connect() as connection:
            self._active_connection = connection
            try:
                yield
            finally:
                self._active_connection = None

    @contextmanager
    def _snowflake_proxy_context(self):
        """Temporarily bypass local proxy variables for Snowflake connections when configured."""
        if not self.settings.snowflake_disable_proxy:
            yield
            return

        proxy_keys = [
            "HTTP_PROXY",
            "HTTPS_PROXY",
            "ALL_PROXY",
            "http_proxy",
            "https_proxy",
            "all_proxy",
        ]
        previous = {key: os.environ.get(key) for key in proxy_keys}
        no_proxy = os.environ.get("NO_PROXY") or os.environ.get("no_proxy") or ""
        no_proxy_parts = {part.strip() for part in no_proxy.split(",") if part.strip()}
        no_proxy_parts.update({"localhost", "127.0.0.1", "::1", ".snowflakecomputing.com"})
        try:
            for key in proxy_keys:
                os.environ.pop(key, None)
            os.environ["NO_PROXY"] = ",".join(sorted(no_proxy_parts))
            yield
        finally:
            for key, value in previous.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value
            if no_proxy:
                os.environ["NO_PROXY"] = no_proxy

    def execute(self, sql: str, parameters: Iterable[Any] | dict[str, Any] | None = None) -> list[dict[str, Any]]:
        """Execute one SQL statement and return rows as lower-case-key dictionaries."""
        connection = self._active_connection
        if connection is not None:
            return self._execute_on_connection(connection, sql, parameters)

        with self.connect() as connection:
            return self._execute_on_connection(connection, sql, parameters)

    def execute_many(self, statements: list[str]) -> None:
        """Execute a list of SQL statements in one Snowflake session."""
        connection = self._active_connection
        if connection is not None:
            self._execute_many_on_connection(connection, statements)
            return

        with self.connect() as connection:
            self._execute_many_on_connection(connection, statements)

    def _execute_on_connection(
        self,
        connection,
        sql: str,
        parameters: Iterable[Any] | dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Execute one statement on an existing Snowflake connection."""
        cursor = connection.cursor()
        try:
            cursor.execute(sql, parameters)
            columns = [column[0].lower() for column in cursor.description or []]
            return [dict(zip(columns, row, strict=False)) for row in cursor.fetchall()] if columns else []
        finally:
            cursor.close()

    def _execute_many_on_connection(self, connection, statements: list[str]) -> None:
        """Execute multiple statements on an existing Snowflake connection."""
        cursor = connection.cursor()
        try:
            for statement in statements:
                if statement.strip():
                    cursor.execute(statement)
            connection.commit()
        finally:
            cursor.close()

    def create_database_objects(self) -> None:
        """Create the configured database, schema, and artifact stage if needed."""
        database = self.settings.snowflake_database
        schema = self.settings.snowflake_schema
        stage = self.settings.snowflake_stage
        self.execute_many(
            [
                f"CREATE DATABASE IF NOT EXISTS {database}",
                f"CREATE SCHEMA IF NOT EXISTS {database}.{schema}",
                f"CREATE STAGE IF NOT EXISTS {database}.{schema}.{stage} ENCRYPTION = (TYPE = 'SNOWFLAKE_SSE')",
            ]
        )

    def ensure_storage_model(self) -> None:
        """Create all platform tables required for conversion, validation, review, and deployment."""
        self.create_database_objects()
        self.execute_many(
            [
                """
                CREATE TABLE IF NOT EXISTS CONVERSION_REQUESTS (
                  request_id STRING PRIMARY KEY,
                  source_name STRING NOT NULL,
                  source_type STRING NOT NULL,
                  package_name STRING,
                  submitted_by STRING NOT NULL,
                  checksum_sha256 STRING NOT NULL,
                  line_count NUMBER,
                  detected_features VARIANT,
                  abap_source STRING NOT NULL,
                  status STRING DEFAULT 'RECEIVED',
                  deployed_version STRING,
                  created_at TIMESTAMP_TZ DEFAULT CURRENT_TIMESTAMP(),
                  completed_at TIMESTAMP_TZ
                )
                """,
                """
                CREATE TABLE IF NOT EXISTS CONVERSION_RESULTS (
                  result_id STRING DEFAULT UUID_STRING(),
                  request_id STRING NOT NULL,
                  generated_sql STRING NOT NULL,
                  confidence FLOAT NOT NULL,
                  artifact_type STRING NOT NULL,
                  warnings VARIANT,
                  assumptions VARIANT,
                  notes VARIANT,
                  created_at TIMESTAMP_TZ DEFAULT CURRENT_TIMESTAMP()
                )
                """,
                """
                CREATE TABLE IF NOT EXISTS METADATA_REPOSITORY (
                  metadata_id STRING DEFAULT UUID_STRING(),
                  object_type STRING NOT NULL,
                  object_name STRING,
                  table_name STRING,
                  table_class STRING,
                  delivery_class STRING,
                  column_name STRING,
                  ordinal_position NUMBER,
                  data_element STRING,
                  domain_name STRING,
                  snowflake_type STRING,
                  semantic_category STRING,
                  is_key BOOLEAN,
                  description STRING,
                  parent_table STRING,
                  parent_column STRING,
                  child_table STRING,
                  child_column STRING,
                  relationship_type STRING,
                  parameter_name STRING,
                  direction STRING,
                  target_exists BOOLEAN DEFAULT TRUE,
                  raw_metadata VARIANT,
                  loaded_at TIMESTAMP_TZ DEFAULT CURRENT_TIMESTAMP()
                )
                """,
                """
                CREATE TABLE IF NOT EXISTS PATTERN_LIBRARY (
                  pattern_id STRING DEFAULT UUID_STRING(),
                  abap_snippet STRING NOT NULL,
                  converted_sql STRING NOT NULL,
                  human_correction STRING,
                  approved_by STRING,
                  approval_score FLOAT DEFAULT 1.0,
                  created_at TIMESTAMP_TZ DEFAULT CURRENT_TIMESTAMP()
                )
                """,
                """
                CREATE TABLE IF NOT EXISTS VALIDATION_RESULTS (
                  validation_id STRING DEFAULT UUID_STRING(),
                  request_id STRING NOT NULL,
                  stage STRING NOT NULL,
                  status STRING NOT NULL,
                  message STRING NOT NULL,
                  diagnostics VARIANT,
                  created_at TIMESTAMP_TZ DEFAULT CURRENT_TIMESTAMP()
                )
                """,
                """
                CREATE TABLE IF NOT EXISTS REVIEW_HISTORY (
                  review_id STRING DEFAULT UUID_STRING(),
                  actor STRING NOT NULL,
                  action STRING NOT NULL,
                  entity_id STRING NOT NULL,
                  details VARIANT,
                  created_at TIMESTAMP_TZ DEFAULT CURRENT_TIMESTAMP()
                )
                """,
                """
                CREATE TABLE IF NOT EXISTS FEEDBACK_DATASET (
                  feedback_id STRING DEFAULT UUID_STRING(),
                  request_id STRING NOT NULL,
                  abap_source STRING,
                  converted_sql STRING NOT NULL,
                  reviewer_sql STRING,
                  validation_summary VARIANT,
                  created_at TIMESTAMP_TZ DEFAULT CURRENT_TIMESTAMP()
                )
                """,
                """
                CREATE TABLE IF NOT EXISTS DEPLOYMENT_RELEASES (
                  release_id STRING DEFAULT UUID_STRING(),
                  request_id STRING NOT NULL,
                  target_name STRING NOT NULL,
                  version STRING NOT NULL,
                  artifact_type STRING NOT NULL,
                  deployed_sql STRING NOT NULL,
                  release_tag STRING NOT NULL,
                  deployed_at TIMESTAMP_TZ DEFAULT CURRENT_TIMESTAMP()
                )
                """,
            ]
        )
