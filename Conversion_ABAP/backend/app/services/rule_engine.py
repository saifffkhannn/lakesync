"""Deterministic rewrite rules applied before AI conversion.

These rules normalize common ABAP/Open SQL idioms and provide confidence hints before
the Snowflake Cortex model receives the source.
"""

import re
from dataclasses import dataclass
from typing import Protocol

from app.schemas.conversion import RuleResult


class ConversionRule(Protocol):
    """Protocol implemented by every deterministic conversion rule."""

    name: str

    def apply(self, sql_or_abap: str) -> tuple[str, float]:
        """Return the rewritten text and confidence delta for one rule."""
        ...


@dataclass(frozen=True)
class RegexRule:
    """Simple regular-expression replacement rule with a fixed confidence delta."""

    name: str
    pattern: re.Pattern[str]
    replacement: str
    confidence_delta: float

    def apply(self, sql_or_abap: str) -> tuple[str, float]:
        """Apply the regex replacement and report its confidence effect."""
        updated, count = self.pattern.subn(self.replacement, sql_or_abap)
        return updated, self.confidence_delta if count else 0.0


class ForAllEntriesRule:
    """Adds an explicit rewrite hint for ABAP FOR ALL ENTRIES semantics."""

    name = "for_all_entries_join_rewrite_hint"

    def apply(self, sql_or_abap: str) -> tuple[str, float]:
        """Replace FOR ALL ENTRIES text with a Snowflake join rewrite hint."""
        if re.search(r"FOR\s+ALL\s+ENTRIES\s+IN", sql_or_abap, re.IGNORECASE):
            rewritten = re.sub(
                r"FOR\s+ALL\s+ENTRIES\s+IN\s+(\w+)",
                r"/* rewrite FOR ALL ENTRIES IN \1 as an explicit JOIN against a staged distinct key set */",
                sql_or_abap,
                flags=re.IGNORECASE,
            )
            return rewritten, 0.04
        return sql_or_abap, 0.0


class RuleEngine:
    """Runs all deterministic conversion rules in a stable order."""

    def __init__(self) -> None:
        """Create the ordered rule list used before AI conversion."""
        self.rules: list[ConversionRule] = [
            RegexRule("select_single_limit", re.compile(r"\bSELECT\s+SINGLE\b", re.IGNORECASE), "SELECT", 0.03),
            RegexRule("sy_datum_current_date", re.compile(r"\bSY-DATUM\b", re.IGNORECASE), "CURRENT_DATE", 0.02),
            RegexRule("sy_uzeit_current_time", re.compile(r"\bSY-UZEIT\b", re.IGNORECASE), "CURRENT_TIME", 0.02),
            RegexRule("remove_mandt_projection", re.compile(r"\bMANDT\s*,?\s*", re.IGNORECASE), "", 0.02),
            ForAllEntriesRule(),
        ]

    def execute(self, source: str) -> tuple[str, list[RuleResult], float]:
        """Apply rules and return rewritten source, applied rule records, and total confidence delta."""
        current = source
        applied: list[RuleResult] = []
        confidence_delta = 0.0
        for rule in self.rules:
            before = current
            current, delta = rule.apply(current)
            if before != current:
                applied.append(
                    RuleResult(
                        rule_name=rule.name,
                        before=before,
                        after=current,
                        confidence_delta=delta,
                    )
                )
                confidence_delta += delta
        return current, applied, min(confidence_delta, 0.15)
