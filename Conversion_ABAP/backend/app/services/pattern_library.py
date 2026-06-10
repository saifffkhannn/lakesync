import json
from typing import Any

from app.services.snowflake_connector import SnowflakeConnector


class PatternLibrary:
    def __init__(self, connector: SnowflakeConnector):
        self.connector = connector

    def retrieve(self, query: str, top_k: int = 5) -> list[dict[str, Any]]:
        try:
            return self.connector.execute(
                """
                SELECT abap_snippet, converted_sql, human_correction, approval_score
                FROM TABLE(CORTEX_SEARCH_DATA_SCAN(
                  SERVICE_NAME => 'PATTERN_LIBRARY_SEARCH',
                  QUERY => %(query)s,
                  LIMIT => %(top_k)s
                ))
                ORDER BY approval_score DESC
                """,
                {"query": query, "top_k": top_k},
            )
        except Exception:
            return []

    def store_feedback(
        self,
        request_id: str,
        abap_source: str,
        converted_sql: str,
        reviewer_sql: str | None,
        validation_summary: dict[str, Any],
    ) -> None:
        self.connector.execute(
            """
            INSERT INTO FEEDBACK_DATASET(request_id, abap_source, converted_sql, reviewer_sql, validation_summary)
            SELECT %(request_id)s, %(abap_source)s, %(converted_sql)s, %(reviewer_sql)s, PARSE_JSON(%(validation)s)
            """,
            {
                "request_id": request_id,
                "abap_source": abap_source,
                "converted_sql": converted_sql,
                "reviewer_sql": reviewer_sql,
                "validation": json.dumps(validation_summary),
            },
        )
