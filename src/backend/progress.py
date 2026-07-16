"""Lightweight request progress tracking for long-running actigraphy analysis.

Progress is kept in memory and mirrored to ``APP_DATA_DIR/progress`` so a
polling request can retrieve updates while a CPU-heavy analysis runs in a
FastAPI threadpool.  The file mirror also helps when a deployment uses more
than one worker sharing the same persistent volume.
"""

from __future__ import annotations

import json
import os
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

_LOCK = threading.RLock()
_RECORDS: Dict[str, Dict[str, Any]] = {}
_TTL_SECONDS = int(os.getenv("ANALYSIS_PROGRESS_TTL_SECONDS", "21600"))

_STAGE_LABELS = {
    "request.parse_analysis_config": "Reading analysis settings",
    "upload.primary_file": "Saving the uploaded recording",
    "input.detect_reader": "Identifying the recording format",
    "input.load_recording": "Decoding and epoching the recording",
    "input.inspect_recording": "Checking timestamps and activity data",
    "upload.support_files": "Loading support files",
    "preprocessing.apply_support_files": "Applying start/stop, masks, and diary windows",
    "analysis.execute": "Running the selected analyses",
    "sleep.algorithm_score": "Scoring sleep and wake epochs",
    "sleep.window_detection": "Detecting sleep/rest windows",
    "analysis.quality_control": "Checking result quality",
    "request.cleanup_temp_files": "Cleaning temporary files",
    "metric.ra": "Calculating Relative Amplitude (RA)",
    "metric.is": "Calculating Interdaily Stability (IS)",
    "metric.iv": "Calculating Intradaily Variability (IV)",
    "metric.ism": "Calculating mean Interdaily Stability (ISm)",
    "metric.ivm": "Calculating mean Intradaily Variability (IVm)",
    "metric.isp": "Calculating IS by period (ISp)",
    "metric.ivp": "Calculating IV by period (IVp)",
    "metric.rap": "Calculating RA by period (RAp)",
    "metric.kra": "Calculating rest-to-activity fragmentation (kRA)",
    "metric.kar": "Calculating activity-to-rest fragmentation (kAR)",
    "metric.sri": "Calculating Sleep Regularity Index (SRI)",
    "metric.tst": "Calculating Total Sleep Time (TST)",
    "metric.waso": "Calculating Wake After Sleep Onset (WASO)",
    "metric.sleep_efficiency": "Calculating Sleep Efficiency",
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def stage_label(name: Optional[str]) -> str:
    if not name:
        return "Preparing analysis"
    if name in _STAGE_LABELS:
        return _STAGE_LABELS[name]
    if name.startswith("metric."):
        return f"Calculating {name.split('.', 1)[1].upper()}"
    return name.replace(".", " · ").replace("_", " ").strip().title()


def _progress_dir() -> Path:
    path = Path(os.getenv("APP_DATA_DIR", "/tmp/actigraphy-ui-data")) / "progress"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _path_for(request_id: str) -> Path:
    safe = "".join(ch for ch in str(request_id) if ch.isalnum() or ch in {"-", "_"})
    return _progress_dir() / f"{safe}.json"


def _write_file(record: Dict[str, Any]) -> None:
    try:
        path = _path_for(record["request_id"])
        tmp = path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(record, ensure_ascii=False, default=str), encoding="utf-8")
        tmp.replace(path)
    except Exception:
        pass


def _cleanup_locked() -> None:
    cutoff = time.time() - _TTL_SECONDS
    expired = [key for key, value in _RECORDS.items() if float(value.get("updated_epoch", 0)) < cutoff]
    for key in expired:
        _RECORDS.pop(key, None)
        try:
            _path_for(key).unlink(missing_ok=True)
        except Exception:
            pass


def start_progress(
    request_id: str,
    *,
    endpoint: str,
    source_file_name: Optional[str] = None,
    total_stages: int = 1,
) -> Dict[str, Any]:
    now = _utc_now()
    record = {
        "request_id": request_id,
        "endpoint": endpoint,
        "source_file_name": source_file_name,
        "status": "running",
        "stage_name": None,
        "stage_label": "Preparing analysis",
        "stage_status": "pending",
        "stage_current": 0,
        "stage_total": max(1, int(total_stages or 1)),
        "stage_fraction": 0.0,
        "percent": 0.0,
        "message": "Preparing analysis",
        "details": {},
        "started_at": now,
        "updated_at": now,
        "updated_epoch": time.time(),
    }
    with _LOCK:
        _cleanup_locked()
        _RECORDS[request_id] = record
        _write_file(record)
    return dict(record)


def set_total(request_id: str, total_stages: int) -> None:
    with _LOCK:
        record = _RECORDS.get(request_id)
        if record is None:
            return
        record["stage_total"] = max(int(total_stages or 1), int(record.get("stage_current", 0)), 1)
        _recalculate(record)
        _touch(record)


def _recalculate(record: Dict[str, Any]) -> None:
    total = max(1, int(record.get("stage_total", 1)))
    current = max(0, int(record.get("stage_current", 0)))
    fraction = min(1.0, max(0.0, float(record.get("stage_fraction", 0.0) or 0.0)))
    completed_before_current = max(0, current - 1)
    if record.get("stage_status") in {"passed", "warning", "failed"}:
        completed_before_current = current
        fraction = 0.0
    percent = ((completed_before_current + fraction) / total) * 100.0
    if record.get("status") == "completed":
        percent = 100.0
    record["percent"] = round(min(100.0, max(0.0, percent)), 1)


def _touch(record: Dict[str, Any]) -> None:
    record["updated_at"] = _utc_now()
    record["updated_epoch"] = time.time()
    _write_file(record)


def update_progress(
    request_id: str,
    *,
    stage_name: Optional[str] = None,
    stage_current: Optional[int] = None,
    stage_total: Optional[int] = None,
    stage_status: Optional[str] = None,
    stage_fraction: Optional[float] = None,
    message: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
) -> None:
    with _LOCK:
        record = _RECORDS.get(request_id)
        if record is None:
            return
        existing_current = int(record.get("stage_current", 0))
        incoming_current = max(0, int(stage_current)) if stage_current is not None else existing_current
        # Nested diagnostic stages can finish after newer inner stages. Do not
        # let an older outer stage overwrite the currently displayed label.
        should_update_stage_identity = stage_name is not None and incoming_current >= existing_current
        if should_update_stage_identity:
            record["stage_name"] = stage_name
            record["stage_label"] = stage_label(stage_name)
        if stage_current is not None:
            record["stage_current"] = max(existing_current, incoming_current)
        if stage_total is not None:
            record["stage_total"] = max(1, int(stage_total), int(record.get("stage_current", 0)))
        elif int(record.get("stage_current", 0)) > int(record.get("stage_total", 1)):
            record["stage_total"] = int(record["stage_current"])
        if stage_status is not None:
            record["stage_status"] = stage_status
        if stage_fraction is not None:
            record["stage_fraction"] = min(1.0, max(0.0, float(stage_fraction)))
        if message is not None:
            record["message"] = message
        elif should_update_stage_identity:
            record["message"] = record["stage_label"]
        if details:
            record.setdefault("details", {}).update(details)
        _recalculate(record)
        _touch(record)


def finish_progress(request_id: str, status: str, message: Optional[str] = None) -> None:
    with _LOCK:
        record = _RECORDS.get(request_id)
        if record is None:
            return
        record["status"] = status
        record["stage_status"] = "passed" if status == "completed" else status
        if status == "completed":
            record["stage_current"] = max(int(record.get("stage_total", 1)), int(record.get("stage_current", 0)))
            record["message"] = message or "Analysis complete"
        else:
            record["message"] = message or "Analysis stopped with an error"
        _recalculate(record)
        _touch(record)


def get_progress(request_id: str) -> Optional[Dict[str, Any]]:
    with _LOCK:
        record = _RECORDS.get(request_id)
        if record is not None:
            return {key: value for key, value in record.items() if key != "updated_epoch"}
    try:
        path = _path_for(request_id)
        if path.exists():
            record = json.loads(path.read_text(encoding="utf-8"))
            if time.time() - float(record.get("updated_epoch", 0)) <= _TTL_SECONDS:
                return {key: value for key, value in record.items() if key != "updated_epoch"}
    except Exception:
        pass
    return None
