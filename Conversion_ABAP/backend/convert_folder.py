"""Folder-based ABAP conversion command.

This module is the implementation behind the repo-level `convert-ai.ps1` shortcut.
It can run either the local deterministic converter or the Snowflake Cortex AI path.
"""

import argparse
import json
import sys
import time
from contextlib import nullcontext
from pathlib import Path

from app.core.config import get_settings
from app.schemas.conversion import ConversionRequest
from app.services.abap_parser import AbapParser
from app.services.cortex_engine import CortexConversionEngine
from app.services.conversion_memory import ConversionMemory
from app.services.ingestion import IngestionService
from app.services.local_sql_converter import LocalSqlConverter
from app.services.metadata import SemanticKnowledgeService
from app.services.pattern_library import PatternLibrary
from app.services.rule_engine import RuleEngine
from app.services.snowflake_connector import SnowflakeConnector


SUPPORTED_SUFFIXES = {".abap", ".txt", ".src", ".clas", ".prog", ".fugr", ".cds"}
SOURCE_ENCODINGS = ("utf-8-sig", "utf-8", "cp1252", "latin-1")


def parse_args() -> argparse.Namespace:
    """Parse CLI options for folder conversion."""
    parser = argparse.ArgumentParser(description="Convert ABAP files from a folder to Snowflake SQL.")
    parser.add_argument("input_folder", help="Folder containing ABAP source files")
    parser.add_argument(
        "--output-folder",
        default="converted_sql",
        help="Folder where generated .sql and .json reports are written",
    )
    parser.add_argument(
        "--upload-snowflake",
        action="store_true",
        help="Convert with Snowflake Cortex and persist request/results using backend/.env credentials",
    )
    parser.add_argument(
        "--skip-storage-setup",
        action="store_true",
        help="Skip CREATE DATABASE/SCHEMA/TABLE setup for faster repeat AI conversions",
    )
    parser.add_argument(
        "--skip-snowflake-persist",
        action="store_true",
        help="Skip inserting request/result audit rows after AI conversion",
    )
    parser.add_argument(
        "--require-ai-success",
        action="store_true",
        help="Fail the file if Cortex cannot return valid structured output instead of using deterministic fallback",
    )
    parser.add_argument(
        "--recursive",
        action="store_true",
        help="Scan input folder recursively",
    )
    return parser.parse_args()


def run_conversion(
    input_folder_path: str,
    output_folder_path: str,
    upload_snowflake: bool = False,
    skip_storage_setup: bool = False,
    skip_snowflake_persist: bool = False,
    require_ai_success: bool = False,
    recursive: bool = False,
) -> int:
    """Convert all supported ABAP files in the requested folder and write SQL/report files."""
    input_folder = Path(input_folder_path).resolve()
    output_folder = Path(output_folder_path).resolve()

    if not input_folder.exists() or not input_folder.is_dir():
        print(f"Input folder does not exist: {input_folder}", file=sys.stderr)
        return 2

    files = sorted(
        path
        for path in (input_folder.rglob("*") if recursive else input_folder.glob("*"))
        if path.is_file() and path.suffix.lower() in SUPPORTED_SUFFIXES
    )
    if not files:
        print(f"No ABAP files found in {input_folder}. Supported suffixes: {sorted(SUPPORTED_SUFFIXES)}")
        return 1

    output_folder.mkdir(parents=True, exist_ok=True)

    settings = get_settings()
    connector = SnowflakeConnector(settings)
    metadata = SemanticKnowledgeService(connector)
    pattern_library = PatternLibrary(connector)
    parser = AbapParser()
    ingestion = IngestionService()
    local_converter = LocalSqlConverter()
    cortex_converter = CortexConversionEngine(connector, settings)
    memory = ConversionMemory(output_folder / "conversion_memory.jsonl")
    rules = RuleEngine()

    if upload_snowflake and not skip_storage_setup:
        connector.ensure_storage_model()

    converted = 0
    failed = 0
    run_started = time.perf_counter()
    snowflake_session = connector.session() if upload_snowflake else nullcontext()
    with snowflake_session:
        for source_path in files:
            try:
                file_started = time.perf_counter()
                print(f"[{source_path.name}] Starting processing...")
                source = _read_source_text(source_path)
                request = ConversionRequest(
                    source_name=source_path.name,
                    source_type=source_path.suffix.lower().lstrip(".") or "abap",
                    abap_source=source,
                    submitted_by="folder-cli",
                )
                artifact = ingestion.ingest(request)
                
                print(f"[{source_path.name}] Parsing ABAP syntax...")
                parsed = parser.parse(artifact.request.abap_source)
                
                if upload_snowflake:
                    print(f"[{source_path.name}] Applying deterministic rules...")
                    deterministic_source, applied_rules, confidence_delta = rules.execute(artifact.request.abap_source)
                    try:
                        print(f"[{source_path.name}] Retrieving Snowflake SAP metadata...")
                        context = metadata.enrich(parsed)
                        context.retrieved_patterns = pattern_library.retrieve(deterministic_source)
                    except Exception as e:
                        print(f"[{source_path.name}] Metadata retrieval failed: {e}")
                        context = _empty_context()
                        
                    print(f"[{source_path.name}] Fetching conversion memory examples...")
                    context.retrieved_patterns.extend(memory.retrieve(artifact.request.abap_source, parsed))
                    
                    print(f"[{source_path.name}] Sending prompt to Snowflake Cortex AI (this may take a moment)...")
                    output = cortex_converter.convert(
                        artifact.request.abap_source,
                        parsed,
                        context,
                        deterministic_source,
                        require_ai_success=require_ai_success,
                    )
                    output.applied_rules = applied_rules
                    output.confidence = min(output.confidence + confidence_delta, 1.0)
                    print(f"[{source_path.name}] Cortex AI translation complete.")
                else:
                    context = _empty_context()
                    context.retrieved_patterns = memory.retrieve(artifact.request.abap_source, parsed)
                    output = local_converter.convert(artifact.request.abap_source, parsed, context)
                memory_entry = memory.store(source_path.name, artifact.request.abap_source, output, parsed, context)
                relative_stem = source_path.relative_to(input_folder).with_suffix("")
                sql_path = output_folder / f"{relative_stem}.sql"
                report_path = output_folder / f"{relative_stem}.json"
                sql_path.parent.mkdir(parents=True, exist_ok=True)
                report_path.parent.mkdir(parents=True, exist_ok=True)

                sql_path.write_text(output.sql + "\n", encoding="utf-8")
                report_path.write_text(
                    json.dumps(
                        {
                            "source": str(source_path),
                            "sql": str(sql_path),
                            "confidence": output.confidence,
                            "warnings": output.warnings,
                            "assumptions": output.assumptions,
                            "conversion_notes": output.conversion_notes,
                            "learning_memory": {
                                "stored": memory_entry is not None,
                                "memory_file": str(memory.path),
                                "retrieved_examples": len(context.retrieved_patterns),
                            },
                            "applied_rules": [rule.model_dump() for rule in output.applied_rules],
                            "ast_annotations": parsed.annotations,
                            "dependencies": parsed.dependency_graph,
                        },
                        indent=2,
                    ),
                    encoding="utf-8",
                )

                if upload_snowflake and not skip_snowflake_persist:
                    _persist_to_snowflake(connector, artifact, output)

                converted += 1
                engine = "Snowflake Cortex" if upload_snowflake else "local converter"
                elapsed = time.perf_counter() - file_started
                print(f"Converted {source_path.name} with {engine} in {elapsed:.2f}s -> {sql_path}")
            except Exception as exc:
                failed += 1
                print(f"Failed {source_path}: {exc}", file=sys.stderr)

    total_elapsed = time.perf_counter() - run_started
    avg_elapsed = total_elapsed / converted if converted else 0
    print(
        f"Done. Converted={converted}, Failed={failed}, "
        f"Elapsed={total_elapsed:.2f}s, AvgPerConvertedFile={avg_elapsed:.2f}s, Output={output_folder}"
    )
    return 0 if failed == 0 else 1

def main() -> int:
    """CLI entry point for converting folders."""
    args = parse_args()
    return run_conversion(
        input_folder_path=args.input_folder,
        output_folder_path=args.output_folder,
        upload_snowflake=args.upload_snowflake,
        skip_storage_setup=args.skip_storage_setup,
        skip_snowflake_persist=args.skip_snowflake_persist,
        require_ai_success=args.require_ai_success,
        recursive=args.recursive,
    )


def _empty_context():
    """Return an empty semantic context when metadata retrieval is unavailable."""
    from app.schemas.conversion import SemanticContext

    return SemanticContext()


def _read_source_text(source_path: Path) -> str:
    """Read ABAP source using common encodings found in SAP exports."""
    last_error: UnicodeDecodeError | None = None
    for encoding in SOURCE_ENCODINGS:
        try:
            return source_path.read_text(encoding=encoding)
        except UnicodeDecodeError as exc:
            last_error = exc
    if last_error:
        raise last_error
    raise UnicodeDecodeError("utf-8", b"", 0, 1, "Unable to decode source file")


def _persist_to_snowflake(connector: SnowflakeConnector, artifact, output) -> None:
    """Persist folder conversion request and result rows into Snowflake."""
    import json

    request = artifact.request
    connector.execute(
        """
        INSERT INTO CONVERSION_REQUESTS(
          request_id, source_name, source_type, package_name, submitted_by,
          checksum_sha256, line_count, detected_features, abap_source, status
        )
        SELECT %(request_id)s, %(source_name)s, %(source_type)s, %(package_name)s, %(submitted_by)s,
               %(checksum)s, %(line_count)s, PARSE_JSON(%(features)s), %(abap_source)s, 'FOLDER_CONVERTED'
        """,
        {
            "request_id": str(request.request_id),
            "source_name": request.source_name,
            "source_type": request.source_type,
            "package_name": request.package_name,
            "submitted_by": request.submitted_by,
            "checksum": artifact.checksum_sha256,
            "line_count": artifact.line_count,
            "features": json.dumps(sorted(artifact.detected_features)),
            "abap_source": request.abap_source,
        },
    )
    connector.execute(
        """
        INSERT INTO CONVERSION_RESULTS(request_id, generated_sql, confidence, artifact_type, warnings, assumptions, notes)
        SELECT %(request_id)s, %(sql)s, %(confidence)s, %(artifact_type)s,
               PARSE_JSON(%(warnings)s), PARSE_JSON(%(assumptions)s), PARSE_JSON(%(notes)s)
        """,
        {
            "request_id": str(request.request_id),
            "sql": output.sql,
            "confidence": output.confidence,
            "artifact_type": output.artifact_type.value,
            "warnings": json.dumps(output.warnings),
            "assumptions": json.dumps(output.assumptions),
            "notes": json.dumps(output.conversion_notes),
        },
    )


if __name__ == "__main__":
    raise SystemExit(main())
