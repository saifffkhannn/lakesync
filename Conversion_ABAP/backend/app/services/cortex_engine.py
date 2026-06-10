"""Snowflake Cortex AI conversion service.

Builds structured prompts from ABAP source, parser output, metadata, deterministic rules,
and learning memory, then validates Cortex responses into conversion artifacts.
"""

import json
import re
from typing import Any

from pydantic import ValidationError

from app.core.config import Settings
from app.schemas.conversion import ConversionOutput, ParsedProgram, SemanticContext
from app.services.snowflake_connector import SnowflakeConnector


class CortexConversionError(RuntimeError):
    """Raised when Cortex output cannot be converted into the expected schema."""

    pass


class CortexConversionEngine:
    """Converts ABAP source to Snowflake SQL using Snowflake Cortex models."""

    def __init__(self, connector: SnowflakeConnector, settings: Settings):
        """Store the Snowflake connector and model/settings configuration."""
        self.connector = connector
        self.settings = settings

    def convert(
        self,
        abap_source: str,
        parsed: ParsedProgram,
        semantic_context: SemanticContext,
        deterministic_source: str,
        retry_context: list[dict[str, Any]] | None = None,
        require_ai_success: bool = False,
    ) -> ConversionOutput:
        """Run the primary AI conversion flow with model fallback and deterministic fallback."""
        prompt = self._build_prompt(abap_source, parsed, semantic_context, deterministic_source, retry_context or [])
        errors: list[str] = []
        for model in self.settings.cortex_model_priority:
            try:
                response = self.connector.execute(
                    "SELECT SNOWFLAKE.CORTEX.COMPLETE(%(model)s, %(prompt)s) AS response",
                    {"model": model, "prompt": prompt},
                )
                raw = response[0]["response"] if response else ""
                parsed_response = self._parse_json_response(raw)
                output = ConversionOutput.model_validate(parsed_response)
                return self._apply_confidence_guardrails(output, parsed)
            except Exception as exc:
                errors.append(f"{model}: {exc}")
        if require_ai_success:
            raise CortexConversionError("Cortex conversion failed for all configured models: " + "; ".join(errors[:3]))
        fallback = self._deterministic_fallback(deterministic_source)
        fallback.warnings.append("Snowflake Cortex conversion failed; deterministic fallback requires human review.")
        fallback.conversion_notes.extend(errors[:3])
        return fallback

    def remediate(
        self,
        failed_sql: str,
        validation_errors: list[dict[str, Any]],
        semantic_context: SemanticContext,
    ) -> ConversionOutput:
        """Ask Cortex to repair SQL that failed validation."""
        prompt = {
            "role": "snowflake_sql_remediation_agent",
            "instruction": "Return only JSON matching the conversion output schema after fixing the SQL.",
            "failed_sql": failed_sql,
            "validation_errors": validation_errors,
            "semantic_context": semantic_context.model_dump(),
        }
        for model in self.settings.cortex_model_priority:
            try:
                response = self.connector.execute(
                    "SELECT SNOWFLAKE.CORTEX.COMPLETE(%(model)s, %(prompt)s) AS response",
                    {"model": model, "prompt": json.dumps(prompt)},
                )
                raw = response[0]["response"] if response else ""
                return ConversionOutput.model_validate(self._parse_json_response(raw))
            except Exception:
                continue
        raise CortexConversionError("Cortex remediation did not return valid structured output")

    def _build_prompt(
        self,
        abap_source: str,
        parsed: ParsedProgram,
        semantic_context: SemanticContext,
        deterministic_source: str,
        retry_context: list[dict[str, Any]],
    ) -> str:
        """Build the compact JSON prompt sent to Cortex."""
        payload = {
            "system": (
                "You are an expert SAP ABAP to Snowflake SQL DDL transpiler. "
                "Your ONLY job is to translate SAP ABAP DDL scripts, table definitions, dictionary objects, and CDS views "
                "directly to their equivalent Snowflake DDL (Data Definition Language) statements with near 100% accuracy. "
                "Do NOT generate views or procedures unless defined in the source (e.g., CDS Views). "
                "Preserve all structural attributes, table columns, constraints, and relationships. "
                "Return strict JSON only."
            ),
            "translation_mode": "DDL_SPECIFIC",
            "translation_rules": [
                "Translate SAP table definitions and DDL structures to Snowflake 'CREATE OR REPLACE TABLE table_name'.",
                "Translate SAP ABAP CDS views ('DEFINE VIEW view_name AS SELECT FROM ...') to Snowflake 'CREATE OR REPLACE VIEW view_name AS SELECT ...'.",
                "Map SAP ABAP data types to Snowflake equivalents precisely:",
                "  - CHAR(n), NUMC(n), CLNT, LANG -> VARCHAR(n)",
                "  - DATS -> DATE",
                "  - TIMS -> TIME",
                "  - DEC(p, s) -> NUMBER(p, s)",
                "  - INT4, INT2, INT1 -> NUMBER",
                "  - FLTP -> FLOAT",
                "  - RAW(n) -> BINARY(n)",
                "  - QUAN(p, s), CURR(p, s) -> NUMBER(p, s)",
                "Preserve primary keys, key columns, and NOT NULL constraints in the created tables.",
                "Strip ABAP annotations like @AbapCatalog, @EndUserText, @AccessControl, @Metadata etc. that are metadata-only.",
                "Translate join conditions, WHERE clauses, and select lists inside CDS views to ANSI/Snowflake syntax.",
                "Convert SAP client dependency checks (e.g. mandt column joins) if required, otherwise map columns normally.",
                "Do NOT add any Snowflake-specific optimizations, clustering, VARIANT columns, or TASK/STREAM wrappers.",
                "The output sql field must contain ONLY the direct SQL DDL translation, nothing else.",
            ],
            "output_schema": {
                "sql": "string - the direct literal SQL DDL translation of the ABAP source",
                "confidence": "number between 0 and 1",
                "warnings": ["string - note any untranslatable DDL structures or types that require manual refactoring"],
                "assumptions": ["string"],
                "conversion_notes": ["string"],
                "artifact_type": "script|view|table",
            },
            "abap_source": abap_source,
            "deterministic_rewrite_input": deterministic_source,
            "typed_ast": parsed.model_dump(),
            "semantic_context": semantic_context.model_dump(),
            "learning_memory": semantic_context.retrieved_patterns,
            "retry_context": retry_context,
        }
        return json.dumps(payload, separators=(",", ":"))

    def _parse_json_response(self, raw: str) -> dict[str, Any]:
        """Extract and parse the JSON object returned by a model."""
        stripped = raw.strip()
        if stripped.startswith("```"):
            stripped = stripped.strip("`")
            stripped = stripped.removeprefix("json").strip()
        start = stripped.find("{")
        end = stripped.rfind("}") + 1
        if start < 0 or end <= start:
            raise CortexConversionError("Response does not contain a JSON object")
        return json.loads(stripped[start:end])

    def _apply_confidence_guardrails(self, output: ConversionOutput, parsed: ParsedProgram) -> ConversionOutput:
        """Cap confidence when warnings or ABAP features indicate material conversion risk."""
        evidence = " ".join(output.warnings + output.assumptions + output.conversion_notes).lower()
        feature_counts = parsed.annotations.get("feature_counts", {})
        cap = 1.0
        reasons: list[str] = []

        severe_terms = [
            "os command",
            "cannot be directly converted",
            "not possible in snowflake",
            "no sql equivalent",
            "not translatable",
            "not suitable for sql conversion",
            "complete application rewrite",
        ]
        major_gap_terms = [
            "omitted",
            "simplified",
            "requires application",
            "application layer",
            "not supported",
            "cannot replicate",
            "must be implemented",
            "requires procedural logic",
        ]
        if any(term in evidence for term in severe_terms):
            cap = min(cap, 0.35)
            reasons.append("Confidence capped because the output identifies core SAP runtime behavior that is not SQL-convertible.")
        elif any(term in evidence for term in major_gap_terms):
            cap = min(cap, 0.65)
            reasons.append("Confidence capped because material behavior is omitted, simplified, or delegated outside SQL.")

        procedural_features = sum(
            int(feature_counts.get(name, 0) or 0)
            for name in ("call_function", "loop", "read_table", "class", "method")
        )
        if procedural_features >= 10:
            cap = min(cap, 0.80)
            reasons.append("Confidence capped because the ABAP contains substantial procedural behavior.")

        if output.confidence > cap:
            output.confidence = cap
            for reason in reasons:
                if reason not in output.warnings:
                    output.warnings.append(reason)
        return output

    def _deterministic_fallback(self, source: str) -> ConversionOutput:
        """Generate a conservative SQL artifact when AI conversion cannot return valid output."""
        compact = re.sub(r"\s+", " ", source).strip().rstrip(".")
        select_match = re.search(
            r"SELECT\s+(?P<columns>.*?)\s+FROM\s+(?P<table>[A-Z0-9_/]+)",
            compact,
            flags=re.IGNORECASE,
        )
        if select_match:
            columns = select_match.group("columns")
            table = select_match.group("table")
            columns = re.sub(r"\bINTO\b.*$", "", columns, flags=re.IGNORECASE).strip()
            columns = re.sub(r"\bSINGLE\b", "", columns, flags=re.IGNORECASE).strip()
            sql = f"SELECT {columns or '*'} FROM {table}"
            if re.search(r"\bSELECT\s+SINGLE\b", compact, flags=re.IGNORECASE):
                sql = f"{sql} LIMIT 1"
        else:
            sql = "SELECT 'Manual review required for unsupported ABAP construct' AS conversion_note"

        return ConversionOutput(
            sql=sql,
            confidence=0.35,
            warnings=["Deterministic fallback cannot guarantee semantic equivalence."],
            assumptions=["Route to human review before deployment."],
            conversion_notes=["Fallback generated because Cortex structured output was unavailable."],
        )
