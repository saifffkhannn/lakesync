import hashlib
from dataclasses import dataclass
from pathlib import PurePath

from app.schemas.conversion import ConversionRequest


@dataclass(frozen=True)
class IngestedArtifact:
    request: ConversionRequest
    checksum_sha256: str
    line_count: int
    detected_features: set[str]


class IngestionService:
    supported_suffixes = {".abap", ".txt", ".src", ".clas", ".prog", ".fugr", ".cds"}

    def ingest(self, request: ConversionRequest) -> IngestedArtifact:
        suffix = PurePath(request.source_name).suffix.lower()
        if suffix and suffix not in self.supported_suffixes:
            raise ValueError(f"Unsupported ABAP artifact suffix: {suffix}")
        source = request.abap_source.replace("\r\n", "\n").strip()
        if not source:
            raise ValueError("ABAP source is empty")

        checksum = hashlib.sha256(source.encode("utf-8")).hexdigest()
        return IngestedArtifact(
            request=request.model_copy(update={"abap_source": source}),
            checksum_sha256=checksum,
            line_count=len(source.splitlines()),
            detected_features=self._detect_features(source),
        )

    def _detect_features(self, source: str) -> set[str]:
        upper = source.upper()
        features = set()
        for token, feature in {
            "SELECT": "open_sql",
            "LOOP AT": "internal_table_loop",
            "READ TABLE": "internal_table_read",
            "COLLECT": "collect_aggregation",
            "CALL FUNCTION": "function_module",
            "CLASS ": "abap_oo",
            "DEFINE VIEW": "cds_view",
            "FOR ALL ENTRIES": "for_all_entries",
            "FIELD-SYMBOLS": "field_symbols",
        }.items():
            if token in upper:
                features.add(feature)
        return features

