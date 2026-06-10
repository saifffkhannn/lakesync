import json
import math
from dataclasses import dataclass
from typing import Any


def _is_blank(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, float) and math.isnan(value):
        return True
    return str(value).strip() == ""


def _first_present(row, names, default=None):
    lookup = {str(col).strip().lower(): col for col in row.index}
    for name in names:
        col = lookup.get(name.strip().lower())
        if col is not None and not _is_blank(row[col]):
            return row[col]
    return default


def _parse_json_or_csv(value, default=None):
    if _is_blank(value):
        return default if default is not None else []

    if isinstance(value, list):
        return value

    text = str(value).strip()
    try:
        parsed = json.loads(text)
        if isinstance(parsed, list):
            return parsed
    except json.JSONDecodeError:
        pass

    return [item.strip() for item in text.split(",") if item.strip()]


def _parse_mapping(value):
    if _is_blank(value):
        return {}

    if isinstance(value, dict):
        return value

    text = str(value).strip()
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid mapping JSON: {text}") from exc

    if not isinstance(parsed, dict):
        raise ValueError("Mapped columns must be a JSON object")

    return {str(k).strip(): str(v).strip() for k, v in parsed.items()}


@dataclass(frozen=True)
class IncrementalTableMetadata:
    source_system: str
    source_database: str
    source_schema: str
    source_table: str
    target_system: str
    target_database: str
    target_schema: str
    target_table: str
    primary_keys: list[str]
    source_columns: list[str]
    target_columns: list[str]
    mapped_columns: dict[str, str]
    watermark_column: str

    @property
    def source_table_name(self) -> str:
        if self.source_schema:
            return f"{self.source_schema}.{self.source_table}"
        return self.source_table

    @property
    def safe_target_table(self) -> str:
        return self.target_table.replace("/", "_")


def normalize_metadata_row(row, default_source: str, default_target: str) -> IncrementalTableMetadata:
    source_sys = str(_first_present(row, ["SOURCE", "source"], default_source)).strip() or default_source

    source_database = str(_first_present(row, ["source_database", "src_db", "DATABASE"])).strip()
    source_schema = str(_first_present(row, ["source_schema", "src_schema", "SCHEMA"])).strip()
    source_table = str(_first_present(row, ["source_table", "src_table", "TABLE"])).strip()

    if source_sys.lower() == "teradata":
        is_db_blank = _is_blank(source_database) or source_database in {"None", "nan"}
        is_schema_blank = _is_blank(source_schema) or source_schema in {"None", "nan"}
        if is_db_blank and not is_schema_blank:
            source_database = source_schema
            source_schema = ""
        if source_schema in {"None", "nan"}:
            source_schema = ""
        if source_database in {"None", "nan"}:
            source_database = ""

    target_database = str(
        _first_present(row, ["target_database", "tgt_db"], source_database)
    ).strip()
    target_schema = str(
        _first_present(row, ["target_schema", "tgt_schema"], source_schema)
    ).strip()
    target_table = str(
        _first_present(row, ["target_table", "tgt_table"], source_table)
    ).strip()

    mapped_columns = _parse_mapping(
        _first_present(row, ["mapped_columns", "column_map_json", "column_mapping"])
    )

    source_columns = _parse_json_or_csv(
        _first_present(row, ["source selected columns", "source_columns_json", "source_columns"])
    )
    target_columns = _parse_json_or_csv(
        _first_present(row, ["target columns", "target_columns_json", "target_columns"])
    )
    primary_keys = _parse_json_or_csv(
        _first_present(row, ["Primary_key_column", "primary_keys", "PRIMARY_KEY"])
    )

    if not source_columns and mapped_columns:
        source_columns = [
            value for value in mapped_columns.values()
            if value and value.upper() not in {"NULL", "DEFAULT"}
        ]
    if not target_columns and mapped_columns:
        target_columns = list(mapped_columns.keys())

    watermark_column = str(
        _first_present(row, ["watermark column(src)", "incremental_col", "watermark_column"])
    ).strip()

    required = {
        "source_database": source_database,
        "source_table": source_table,
        "target_database": target_database,
        "target_schema": target_schema,
        "target_table": target_table,
        "watermark_column": watermark_column,
    }
    if source_sys.lower() != "teradata":
        required["source_schema"] = source_schema

    missing = [name for name, value in required.items() if _is_blank(value)]
    if missing:
        raise ValueError(f"Missing required metadata fields: {', '.join(missing)}")

    if not primary_keys:
        raise ValueError(f"Primary key metadata is required for {source_schema}.{source_table}" if source_schema else f"Primary key metadata is required for {source_table}")

    if watermark_column not in source_columns:
        source_columns = source_columns + [watermark_column]

    return IncrementalTableMetadata(
        source_system=source_sys,
        source_database=source_database,
        source_schema=source_schema,
        source_table=source_table,
        target_system=str(_first_present(row, ["target"], default_target)).strip() or default_target,
        target_database=target_database,
        target_schema=target_schema,
        target_table=target_table,
        primary_keys=primary_keys,
        source_columns=source_columns,
        target_columns=target_columns,
        mapped_columns=mapped_columns,
        watermark_column=watermark_column,
    )


def target_watermark_column(table_metadata: IncrementalTableMetadata) -> str:
    watermark = table_metadata.watermark_column.lower()
    for target_column, source_expression in table_metadata.mapped_columns.items():
        if str(source_expression).strip().lower() == watermark:
            return target_column
    return table_metadata.watermark_column


def target_primary_key_columns(table_metadata: IncrementalTableMetadata) -> list[str]:
    target_keys = []
    for primary_key in table_metadata.primary_keys:
        key = str(primary_key).strip()
        matched_target = None
        for target_column, source_expression in table_metadata.mapped_columns.items():
            if str(source_expression).strip().lower() == key.lower():
                matched_target = target_column
                break
        target_keys.append(matched_target or key)
    return target_keys

