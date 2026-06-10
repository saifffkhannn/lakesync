from functools import lru_cache
from typing import Any

from app.schemas.conversion import ParsedProgram, SemanticContext
from app.services.snowflake_connector import SnowflakeConnector


class SemanticKnowledgeService:
    def __init__(self, connector: SnowflakeConnector):
        self.connector = connector

    def enrich(self, parsed: ParsedProgram) -> SemanticContext:
        tables = parsed.dependency_graph.get("tables", [])
        functions = parsed.dependency_graph.get("function_modules", [])
        return SemanticContext(
            tables=self._table_metadata(tuple(tables)),
            columns=self._column_metadata(tuple(tables)),
            domains=self._domain_metadata(tuple(tables)),
            relationships=self._relationships(tuple(tables)),
            function_signatures=self._function_signatures(tuple(functions)),
        )

    @lru_cache(maxsize=512)
    def _table_metadata(self, tables: tuple[str, ...]) -> list[dict[str, Any]]:
        if not tables:
            return []
        return self.connector.execute(
            """
            SELECT table_name, table_class, description, delivery_class
            FROM METADATA_REPOSITORY
            WHERE object_type = 'DD02L'
              AND table_name IN (SELECT VALUE FROM TABLE(SPLIT_TO_TABLE(%(tables)s, ',')))
            """,
            {"tables": ",".join(tables)},
        )

    @lru_cache(maxsize=512)
    def _column_metadata(self, tables: tuple[str, ...]) -> list[dict[str, Any]]:
        if not tables:
            return []
        return self.connector.execute(
            """
            SELECT table_name, column_name, data_element, domain_name, snowflake_type, description, is_key
            FROM METADATA_REPOSITORY
            WHERE object_type = 'DD03L'
              AND table_name IN (SELECT VALUE FROM TABLE(SPLIT_TO_TABLE(%(tables)s, ',')))
            ORDER BY table_name, ordinal_position
            """,
            {"tables": ",".join(tables)},
        )

    @lru_cache(maxsize=512)
    def _domain_metadata(self, tables: tuple[str, ...]) -> list[dict[str, Any]]:
        if not tables:
            return []
        return self.connector.execute(
            """
            SELECT DISTINCT domain_name, data_element, snowflake_type, semantic_category
            FROM METADATA_REPOSITORY
            WHERE object_type = 'DD04L'
              AND table_name IN (SELECT VALUE FROM TABLE(SPLIT_TO_TABLE(%(tables)s, ',')))
            """,
            {"tables": ",".join(tables)},
        )

    @lru_cache(maxsize=512)
    def _relationships(self, tables: tuple[str, ...]) -> list[dict[str, Any]]:
        if not tables:
            return []
        return self.connector.execute(
            """
            SELECT parent_table, parent_column, child_table, child_column, relationship_type
            FROM METADATA_REPOSITORY
            WHERE object_type = 'DD08L'
              AND (
                parent_table IN (SELECT VALUE FROM TABLE(SPLIT_TO_TABLE(%(tables)s, ',')))
                OR child_table IN (SELECT VALUE FROM TABLE(SPLIT_TO_TABLE(%(tables)s, ',')))
              )
            """,
            {"tables": ",".join(tables)},
        )

    @lru_cache(maxsize=512)
    def _function_signatures(self, functions: tuple[str, ...]) -> list[dict[str, Any]]:
        if not functions:
            return []
        return self.connector.execute(
            """
            SELECT object_name, parameter_name, direction, data_element, snowflake_type
            FROM METADATA_REPOSITORY
            WHERE object_type IN ('BAPI', 'FUNCTION_MODULE')
              AND object_name IN (SELECT VALUE FROM TABLE(SPLIT_TO_TABLE(%(functions)s, ',')))
            """,
            {"functions": ",".join(functions)},
        )
