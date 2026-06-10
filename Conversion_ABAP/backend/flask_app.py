"""Flask bridge API for the React Native upload and conversion app."""

import json
from pathlib import Path
from uuid import uuid4

from flask import Flask, jsonify, request
from werkzeug.utils import secure_filename

from app.core.config import get_settings
from app.schemas.conversion import ConversionRequest
from app.services.ingestion import IngestedArtifact, IngestionService
from app.services.snowflake_connector import SnowflakeConnector
from convert_folder import SUPPORTED_SUFFIXES, run_conversion


BACKEND_DIR = Path(__file__).resolve().parent
PROJECT_DIR = BACKEND_DIR.parent
UI_RUNS_DIR = BACKEND_DIR / "output" / "ui_runs"
SOURCE_ENCODINGS = ("utf-8-sig", "utf-8", "cp1252", "latin-1")
UI_CONVERSION_ENGINE = "Snowflake Cortex"

app = Flask(__name__)


@app.after_request
def add_cors_headers(response):
    """Allow the React Native development server to call the Flask API."""
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    return response


@app.errorhandler(Exception)
def handle_unexpected_error(exc):
    """Return JSON errors so browser fetch calls do not fail as opaque network errors."""
    app.logger.exception("Unhandled Flask bridge error")
    return jsonify({"detail": f"Backend error: {exc}"}), 500


@app.get("/")
def index():
    """Return a lightweight status response for the frontend API bridge."""
    return jsonify({"status": "ok", "service": "abap-conversion-flask-api"})


@app.get("/health")
def health():
    """Return API health for local development checks."""
    return jsonify({"status": "ok"})


@app.route("/convert", methods=["OPTIONS"])
@app.route("/upload-snowflake", methods=["OPTIONS"])
def options_response():
    """Respond to browser preflight requests from Expo Web."""
    return ("", 204)


@app.post("/convert")
def convert_upload():
    """Save an uploaded ABAP file, run folder conversion, and return generated SQL."""
    uploaded = request.files.get("file")
    if uploaded is None or not uploaded.filename:
        return jsonify({"detail": "Upload an ABAP source file first"}), 400

    filename = secure_filename(uploaded.filename) or "uploaded.abap"
    suffix = Path(filename).suffix.lower()
    if suffix not in SUPPORTED_SUFFIXES:
        return jsonify({"detail": f"Unsupported file type. Supported suffixes: {sorted(SUPPORTED_SUFFIXES)}"}), 400

    run_id = uuid4().hex
    input_folder = UI_RUNS_DIR / run_id / "input"
    output_folder = UI_RUNS_DIR / run_id / "output"
    input_folder.mkdir(parents=True, exist_ok=True)
    output_folder.mkdir(parents=True, exist_ok=True)

    source_path = input_folder / filename
    uploaded.save(source_path)

    result, engine, fallback_reason = _run_ui_conversion(input_folder, output_folder)

    if result != 0:
        return jsonify({"detail": "Conversion finished with errors. Check backend logs for details."}), 500

    sql_path = output_folder / f"{source_path.stem}.sql"
    report_path = output_folder / f"{source_path.stem}.json"
    if not sql_path.exists():
        return jsonify({"detail": "Conversion did not produce a SQL output file"}), 500

    source = _read_text(source_path)
    sql = sql_path.read_text(encoding="utf-8")
    report = _read_report(report_path)
    warnings = list(report.get("warnings", []))
    notes = list(report.get("conversion_notes", []))
    if fallback_reason:
        warnings.insert(0, fallback_reason)
        notes.insert(0, "The UI returned a deterministic fallback because AI conversion was unavailable.")
    return jsonify(
        {
            "run_id": run_id,
            "engine": engine,
            "source_name": filename,
            "source": source,
            "sql": sql,
            "download_name": _sql_download_name(filename),
            "confidence": report.get("confidence", 0),
            "warnings": warnings,
            "assumptions": report.get("assumptions", []),
            "conversion_notes": notes,
            "artifact_type": "script",
            "line_count": len(source.splitlines()),
            "detected_features": sorted((report.get("ast_annotations") or {}).get("feature_counts", {}).keys()),
        }
    )


@app.post("/upload-snowflake")
def upload_snowflake():
    """Persist the displayed source and SQL to Snowflake before download."""
    payload = request.get_json(silent=True) or {}
    source = str(payload.get("source") or "")
    sql = str(payload.get("sql") or "")
    source_name = str(payload.get("source_name") or "uploaded.abap")
    if not source.strip() or not sql.strip():
        return jsonify({"detail": "Source and converted SQL are required"}), 400

    try:
        request_model = ConversionRequest(
            source_name=source_name,
            source_type=Path(source_name).suffix.lower().lstrip(".") or "abap",
            abap_source=source,
            submitted_by="browser-ui",
        )
        artifact = IngestionService().ingest(request_model)
        connector = SnowflakeConnector(get_settings())
        connector.ensure_storage_model()
        _persist_displayed_conversion(connector, artifact, payload)
    except Exception as exc:
        return jsonify({"detail": f"Snowflake upload failed: {exc}"}), 500

    return jsonify({"status": "uploaded", "request_id": str(artifact.request.request_id)})


def _read_text(path: Path) -> str:
    """Read ABAP source using common encodings found in SAP exports."""
    for encoding in SOURCE_ENCODINGS:
        try:
            return path.read_text(encoding=encoding)
        except UnicodeDecodeError:
            continue
    return path.read_text(encoding="latin-1")


def _run_ui_conversion(input_folder: Path, output_folder: Path) -> tuple[int, str, str | None]:
    """Run the UI conversion path reliably and return the generated files."""
    result = run_conversion(
        input_folder_path=str(input_folder),
        output_folder_path=str(output_folder),
        upload_snowflake=True,
        skip_storage_setup=True,
        skip_snowflake_persist=True,
        require_ai_success=True,
        recursive=True
    )
    return result, UI_CONVERSION_ENGINE, None


def _read_report(path: Path) -> dict[str, object]:
    """Return a conversion report, or an empty report if it is unavailable."""
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _sql_download_name(source_name: str) -> str:
    """Return a stable .sql download name for an uploaded source artifact."""
    stem = Path(source_name).stem
    safe_stem = "".join(char if char.isalnum() or char in {"-", "_"} else "_" for char in stem).strip("_")
    return f"{safe_stem or 'converted'}.sql"


def _persist_displayed_conversion(
    connector: SnowflakeConnector,
    artifact: IngestedArtifact,
    payload: dict[str, object],
) -> None:
    """Insert the browser-reviewed source and SQL into Snowflake storage tables."""
    request_model = artifact.request
    warnings = payload.get("warnings") if isinstance(payload.get("warnings"), list) else []
    assumptions = payload.get("assumptions") if isinstance(payload.get("assumptions"), list) else []
    notes = payload.get("conversion_notes") if isinstance(payload.get("conversion_notes"), list) else []
    connector.execute(
        """
        INSERT INTO CONVERSION_REQUESTS(
          request_id, source_name, source_type, package_name, submitted_by,
          checksum_sha256, line_count, detected_features, abap_source, status
        )
        SELECT %(request_id)s, %(source_name)s, %(source_type)s, %(package_name)s, %(submitted_by)s,
               %(checksum)s, %(line_count)s, PARSE_JSON(%(features)s), %(abap_source)s, 'UI_CONVERTED'
        """,
        {
            "request_id": str(request_model.request_id),
            "source_name": request_model.source_name,
            "source_type": request_model.source_type,
            "package_name": request_model.package_name,
            "submitted_by": request_model.submitted_by,
            "checksum": artifact.checksum_sha256,
            "line_count": artifact.line_count,
            "features": json.dumps(sorted(artifact.detected_features)),
            "abap_source": request_model.abap_source,
        },
    )
    connector.execute(
        """
        INSERT INTO CONVERSION_RESULTS(request_id, generated_sql, confidence, artifact_type, warnings, assumptions, notes)
        SELECT %(request_id)s, %(sql)s, %(confidence)s, %(artifact_type)s,
               PARSE_JSON(%(warnings)s), PARSE_JSON(%(assumptions)s), PARSE_JSON(%(notes)s)
        """,
        {
            "request_id": str(request_model.request_id),
            "sql": str(payload["sql"]),
            "confidence": float(payload.get("confidence") or 0),
            "artifact_type": str(payload.get("artifact_type") or "script"),
            "warnings": json.dumps(warnings),
            "assumptions": json.dumps(assumptions),
            "notes": json.dumps(notes),
        },
    )


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False, use_reloader=False, threaded=True)
