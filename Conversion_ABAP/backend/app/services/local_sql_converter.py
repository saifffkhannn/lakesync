"""Deterministic local ABAP-to-Snowflake SQL converter.

Used for offline conversion, tests, and fallback-style SQL extraction when Cortex AI is not requested.
"""

import re
from dataclasses import dataclass
from pathlib import Path

from app.schemas.conversion import ConversionOutput, ParsedProgram, SemanticContext


@dataclass(frozen=True)
class LocalConversionArtifact:
    """File paths and conversion output produced by a local conversion run."""

    source_path: Path
    sql_path: Path
    report_path: Path
    output: ConversionOutput


class LocalSqlConverter:
    """Converts common ABAP/Open SQL statements with deterministic regex-based rules."""

    def convert(self, source: str, parsed: ParsedProgram, context: SemanticContext) -> ConversionOutput:
        """Convert ABAP source into Snowflake SQL fragments and a confidence report."""
        statements = self._split_abap_statements(source)
        sql_fragments: list[str] = []
        warnings: list[str] = []
        notes: list[str] = []

        for statement in statements:
            converted = self._convert_statement(statement)
            if converted:
                sql_fragments.append(converted)
            else:
                warnings.append(f"Manual review required for ABAP statement: {statement[:160]}")

        if not sql_fragments:
            sql_fragments.append("SELECT 'Manual review required for unsupported ABAP source' AS conversion_note")

        if parsed.annotations.get("contains_for_all_entries"):
            warnings.append("FOR ALL ENTRIES needs validation against duplicate and empty-driver-table semantics.")
        if context.columns:
            notes.append("SAP metadata was available for semantic review.")
        else:
            notes.append("No SAP metadata rows were found; conversion used source-only inference.")

        confidence = 0.72 if not warnings else 0.48
        return ConversionOutput(
            sql=";\n\n".join(sql_fragments) + ";",
            confidence=confidence,
            warnings=warnings,
            assumptions=[
                "ABAP host variables are emitted as Snowflake bind-style placeholders where possible.",
                "MANDT client handling is removed unless explicitly represented in business filters.",
            ],
            conversion_notes=notes,
        )

    def _split_abap_statements(self, source: str) -> list[str]:
        """Split ABAP source into period-terminated statements while skipping comments."""
        statements: list[str] = []
        current: list[str] = []
        for raw_line in source.replace("\r\n", "\n").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("*"):
                continue
            current.append(line)
            if line.endswith("."):
                statements.append(re.sub(r"\s+", " ", " ".join(current)).strip().rstrip("."))
                current = []
        if current:
            statements.append(re.sub(r"\s+", " ", " ".join(current)).strip().rstrip("."))
        return statements

    def _convert_statement(self, statement: str) -> str | None:
        """Route a single ABAP statement to a supported deterministic conversion."""
        upper = statement.upper()
        if upper.startswith("SELECT"):
            return self._convert_select(statement)
        if upper.startswith("LOOP AT"):
            return self._comment(statement, "ABAP internal table loop requires set-based SQL rewrite")
        if upper.startswith("READ TABLE"):
            return self._comment(statement, "ABAP internal table lookup requires join or QUALIFY rewrite")
        if upper.startswith("COLLECT"):
            return self._comment(statement, "ABAP COLLECT usually maps to GROUP BY aggregation")
        if upper.startswith("CALL FUNCTION"):
            return self._comment(statement, "Function module or BAPI requires procedure/UDF mapping")
        return None

    def _convert_select(self, statement: str) -> str:
        """Rewrite an ABAP SELECT statement into Snowflake-flavored SQL."""
        normalized = self._normalize_abap_tokens(statement)
        is_single = bool(re.search(r"\bSELECT\s+SINGLE\b", normalized, re.IGNORECASE))
        normalized = re.sub(r"\bSELECT\s+SINGLE\b", "SELECT", normalized, flags=re.IGNORECASE)

        normalized = re.sub(r"\s+INTO\s+(?:TABLE\s+)?@?DATA\([^)]*\)", "", normalized, flags=re.IGNORECASE)
        normalized = re.sub(r"\s+INTO\s+(?:TABLE\s+)?[@\w<>\[\]-]+", "", normalized, flags=re.IGNORECASE)
        normalized = re.sub(r"\s+CLIENT\s+SPECIFIED\b", "", normalized, flags=re.IGNORECASE)
        normalized = re.sub(r"\bSELECT\s+MANDT\s+", "SELECT ", normalized, flags=re.IGNORECASE)
        normalized = re.sub(r"\bMANDT\s*,\s*", "", normalized, flags=re.IGNORECASE)
        normalized = re.sub(r",\s*MANDT\b", "", normalized, flags=re.IGNORECASE)
        normalized = re.sub(r"\bMANDT\b\s*=\s*[@:\w'-]+\s*(AND\s*)?", "", normalized, flags=re.IGNORECASE)
        normalized = re.sub(r"\bSY-DATUM\b", "CURRENT_DATE", normalized, flags=re.IGNORECASE)
        normalized = re.sub(r"\bSY-UZEIT\b", "CURRENT_TIME", normalized, flags=re.IGNORECASE)
        normalized = re.sub(r"@([A-Za-z_][A-Za-z0-9_]*)", r":\1", normalized)
        normalized = re.sub(r"\s+", " ", normalized).strip()

        if is_single and not re.search(r"\bLIMIT\s+\d+\b", normalized, re.IGNORECASE):
            normalized = f"{normalized} LIMIT 1"
        return normalized

    def _normalize_abap_tokens(self, statement: str) -> str:
        """Normalize ABAP comparison and table-alias syntax into SQL-like tokens."""
        return (
            statement.replace("~", ".")
            .replace("<>", "!=")
            .replace(" EQ ", " = ")
            .replace(" NE ", " != ")
            .replace(" GT ", " > ")
            .replace(" LT ", " < ")
            .replace(" GE ", " >= ")
            .replace(" LE ", " <= ")
        )

    def _comment(self, statement: str, reason: str) -> str:
        """Emit unsupported procedural ABAP as an explanatory SQL block comment."""
        escaped = statement.replace("*/", "* /")
        return f"/* {reason}\nABAP: {escaped}\n*/"
