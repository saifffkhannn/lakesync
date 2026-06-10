import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.schemas.conversion import ConversionOutput, ParsedProgram, SemanticContext


class ConversionMemory:
    def __init__(self, path: Path | None = None):
        self.path = path or Path("conversion_memory.jsonl")

    def retrieve(self, source: str, parsed: ParsedProgram, top_k: int = 5) -> list[dict[str, Any]]:
        entries = self._read_entries()
        if not entries:
            return []

        source_tokens = self._tokens(source)
        source_features = set(parsed.annotations.get("feature_counts", {}).keys())
        scored: list[tuple[float, dict[str, Any]]] = []
        for entry in entries:
            entry_tokens = set(entry.get("tokens", []))
            feature_overlap = len(source_features.intersection(entry.get("feature_counts", {}).keys()))
            token_overlap = len(source_tokens.intersection(entry_tokens))
            score = token_overlap + (feature_overlap * 3) + float(entry.get("severity", 0))
            if score > 0:
                scored.append((score, entry))

        scored.sort(key=lambda item: item[0], reverse=True)
        return [self._prompt_example(entry) for _, entry in scored[:top_k]]

    def store(
        self,
        source_name: str,
        source: str,
        output: ConversionOutput,
        parsed: ParsedProgram,
        context: SemanticContext,
    ) -> dict[str, Any] | None:
        gaps = self._extract_gaps(output)
        if not gaps:
            return None

        entry = {
            "id": self._fingerprint(source, gaps),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "source_name": source_name,
            "abap_snippet": self._snippet(source),
            "generated_sql_snippet": self._snippet(output.sql),
            "confidence": output.confidence,
            "artifact_type": output.artifact_type,
            "gaps": gaps,
            "severity": self._severity(output, gaps),
            "feature_counts": parsed.annotations.get("feature_counts", {}),
            "dependencies": parsed.dependency_graph,
            "metadata_available": bool(context.tables or context.columns or context.function_signatures),
            "tokens": sorted(self._tokens(source + " " + " ".join(gaps))),
        }
        self._append_unique(entry)
        return entry

    def _read_entries(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        entries: list[dict[str, Any]] = []
        for line in self.path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        return entries

    def _append_unique(self, entry: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if any(existing.get("id") == entry["id"] for existing in self._read_entries()):
            return
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry, sort_keys=True) + "\n")

    def _extract_gaps(self, output: ConversionOutput) -> list[str]:
        candidates = output.warnings + output.assumptions + output.conversion_notes
        gap_markers = (
            "cannot",
            "manual review",
            "requires",
            "not supported",
            "not suitable",
            "omitted",
            "application layer",
            "fallback",
            "unsupported",
            "not converted",
            "not translatable",
        )
        gaps = []
        for candidate in candidates:
            normalized = re.sub(r"\s+", " ", candidate).strip()
            if normalized and any(marker in normalized.lower() for marker in gap_markers):
                gaps.append(normalized)
        return list(dict.fromkeys(gaps))

    def _prompt_example(self, entry: dict[str, Any]) -> dict[str, Any]:
        return {
            "source_name": entry.get("source_name"),
            "abap_snippet": entry.get("abap_snippet"),
            "previous_confidence": entry.get("confidence"),
            "previous_gaps": entry.get("gaps", []),
            "guidance": (
                "Avoid repeating these unresolved conversion gaps. If the same ABAP pattern appears, "
                "either produce a better Snowflake implementation or explicitly route only the non-SQL "
                "runtime behavior to manual/application-layer work."
            ),
        }

    def _severity(self, output: ConversionOutput, gaps: list[str]) -> int:
        severe = sum(1 for gap in gaps if "cannot" in gap.lower() or "unsupported" in gap.lower())
        return severe + max(0, int((0.86 - output.confidence) * 10))

    def _fingerprint(self, source: str, gaps: list[str]) -> str:
        payload = f"{self._snippet(source, 500)}\n{'|'.join(gaps)}"
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def _snippet(self, text: str, limit: int = 1200) -> str:
        compact = re.sub(r"\s+", " ", text).strip()
        return compact[:limit]

    def _tokens(self, text: str) -> set[str]:
        stop_words = {"the", "and", "for", "with", "from", "into", "data", "type"}
        return {
            token
            for token in re.findall(r"[A-Za-z_][A-Za-z0-9_]{2,}", text.upper())
            if token.lower() not in stop_words
        }
