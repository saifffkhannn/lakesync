import threading
from datetime import datetime
from typing import Any, Dict, List, Optional


pipeline_state: Dict[str, Any] = {
    "progress": 0,
    "table_status": [],
    "logs": [],
    "current_log_file": None,
}

_lock = threading.Lock()


def _utc_now_iso() -> str:
    return datetime.utcnow().isoformat()


def _parse_iso(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None

    try:
        return datetime.fromisoformat(value)
    except Exception:
        return None


def _get_or_create_table_locked(table: str) -> Dict[str, Any]:
    existing = next(
        (item for item in pipeline_state["table_status"] if item["table"] == table),
        None,
    )

    if existing:
        return existing

    created = {
        "table": table,
        "status": "pending",
        "source_row_count": None,
        "target_row_count": None,
        "duration_seconds": None,
        "started_at": None,
        "finished_at": None,
    }
    pipeline_state["table_status"].append(created)
    return created


def _build_steps(status: str) -> Dict[str, str]:
    normalized = str(status or "pending").lower()

    if normalized in {"completed", "success"}:
        return {"extraction": "completed", "upload": "completed", "load": "completed"}

    if normalized in {"loading"}:
        return {"extraction": "completed", "upload": "completed", "load": "in_progress"}

    if normalized in {"uploaded", "creating_table"}:
        return {"extraction": "completed", "upload": "completed", "load": "pending"}

    if normalized in {"uploading"}:
        return {"extraction": "completed", "upload": "in_progress", "load": "pending"}

    if normalized in {"extracted"}:
        return {"extraction": "completed", "upload": "pending", "load": "pending"}

    if normalized in {"extracting"}:
        return {"extraction": "in_progress", "upload": "pending", "load": "pending"}

    if normalized in {"upload_failed"}:
        return {"extraction": "completed", "upload": "failed", "load": "pending"}

    if normalized in {"load_failed", "table_creation_failed", "validation_failed"}:
        return {"extraction": "completed", "upload": "completed", "load": "failed"}

    if normalized in {"extraction_failed", "failed"}:
        return {"extraction": "failed", "upload": "pending", "load": "pending"}

    return {"extraction": "pending", "upload": "pending", "load": "pending"}


def _compute_duration_seconds(item: Dict[str, Any]) -> Optional[float]:
    started_at = _parse_iso(item.get("started_at"))
    finished_at = _parse_iso(item.get("finished_at"))

    if not started_at:
        return item.get("duration_seconds")

    effective_end = finished_at or datetime.utcnow()
    return max(0.0, round((effective_end - started_at).total_seconds(), 2))


def reset_pipeline_state(log_file: Optional[str] = None, table_status: Optional[List[Dict[str, str]]] = None) -> None:
    with _lock:
        pipeline_state["progress"] = 0
        pipeline_state["table_status"] = [
            {
                "table": item.get("table"),
                "status": item.get("status", "pending"),
                "source_row_count": item.get("source_row_count"),
                "target_row_count": item.get("target_row_count"),
                "duration_seconds": item.get("duration_seconds"),
                "started_at": item.get("started_at"),
                "finished_at": item.get("finished_at"),
            }
            for item in (table_status or [])
        ]
        pipeline_state["logs"] = []
        pipeline_state["current_log_file"] = log_file


def append_log(message: str) -> None:
    with _lock:
        pipeline_state["logs"].append(message)


def set_current_log_file(log_file: Optional[str]) -> None:
    with _lock:
        pipeline_state["current_log_file"] = log_file


def update_table_status(table: str, status: str) -> None:
    with _lock:
        existing = _get_or_create_table_locked(table)

        if existing.get("status") == status:
            return

        existing["status"] = status

        if status == "extracting" and not existing.get("started_at"):
            existing["started_at"] = _utc_now_iso()
            existing["finished_at"] = None

        if status in {
            "completed",
            "failed",
            "extraction_failed",
            "upload_failed",
            "table_creation_failed",
            "load_failed",
            "validation_failed",
        }:
            if existing.get("started_at"):
                existing["finished_at"] = existing.get("finished_at") or _utc_now_iso()
                existing["duration_seconds"] = _compute_duration_seconds(existing)

        event = _format_status_event(table, status)
        if event:
            pipeline_state["logs"].append(event)

        _recalculate_progress_locked()


def update_table_metrics(
    table: str,
    source_row_count: Optional[int] = None,
    target_row_count: Optional[int] = None,
    duration_seconds: Optional[float] = None,
    started_at: Optional[str] = None,
    finished_at: Optional[str] = None,
) -> None:
    with _lock:
        existing = _get_or_create_table_locked(table)

        if source_row_count is not None:
            existing["source_row_count"] = source_row_count

        if target_row_count is not None:
            existing["target_row_count"] = target_row_count

        if started_at is not None:
            existing["started_at"] = started_at

        if finished_at is not None:
            existing["finished_at"] = finished_at

        if duration_seconds is not None:
            existing["duration_seconds"] = round(duration_seconds, 2)
        else:
            existing["duration_seconds"] = _compute_duration_seconds(existing)


def _format_status_event(table: str, status: str) -> Optional[str]:
    labels = {
        "pending": f"{table}: queued for migration.",
        "extracting": f"{table}: extracting from source.",
        "extracted": f"{table}: extraction completed.",
        "uploading": f"{table}: uploading parquet to cloud storage.",
        "uploaded": f"{table}: upload completed.",
        "creating_table": f"{table}: creating target objects.",
        "loading": f"{table}: loading into target.",
        "completed": f"{table}: migration completed.",
        "extraction_failed": f"{table}: extraction failed. Download the run log for details.",
        "upload_failed": f"{table}: upload failed. Download the run log for details.",
        "table_creation_failed": f"{table}: target table creation failed. Download the run log for details.",
        "load_failed": f"{table}: load failed. Download the run log for details.",
        "validation_failed": f"{table}: validation failed. Row counts did not match.",
        "failed": f"{table}: migration failed. Download the run log for details.",
    }

    return labels.get(status)


def _recalculate_progress_locked() -> None:
    table_status = pipeline_state["table_status"]
    if not table_status:
        pipeline_state["progress"] = 0
        return

    step_score = {
        "pending": 0,
        "extracting": 0,
        "extracted": 1,
        "uploading": 1,
        "uploaded": 2,
        "creating_table": 2,
        "loading": 2,
        "completed": 3,
        "failed": 0,
        "extraction_failed": 0,
        "upload_failed": 1,
        "load_failed": 2,
        "table_creation_failed": 2,
        "validation_failed": 2,
    }

    completed_steps = 0
    total_steps = len(table_status) * 3

    for item in table_status:
        completed_steps += step_score.get(str(item.get("status", "pending")), 0)

    pipeline_state["progress"] = int((completed_steps / total_steps) * 100)


def set_progress(progress: int) -> None:
    with _lock:
        pipeline_state["progress"] = max(0, min(100, progress))


def get_pipeline_snapshot() -> Dict[str, Any]:
    with _lock:
        return {
            "progress": pipeline_state.get("progress", 0),
            "table_status": [
                {
                    **dict(item),
                    "duration_seconds": _compute_duration_seconds(item),
                    "steps": _build_steps(str(item.get("status", "pending"))),
                }
                for item in pipeline_state.get("table_status", [])
            ],
            "logs": list(pipeline_state.get("logs", [])),
            "current_log_file": pipeline_state.get("current_log_file"),
        }
