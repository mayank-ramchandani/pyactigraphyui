"""Structured, low-overhead diagnostics for actigraphy web requests.

Diagnostics are returned with API responses so administrators can distinguish
transport/upload, reader/conversion, preprocessing, sleep-window, and individual
metric failures.  The helpers are intentionally defensive: diagnostic collection
must never become the reason an analysis request fails.
"""

from __future__ import annotations

import contextvars
import hashlib
import importlib.metadata
import json
import logging
import math
import os
import platform
import resource
import shutil
import sys
import time
import traceback
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

import pandas as pd

try:  # Optional at import time; requirements include it for deployed builds.
    import psutil
except Exception:  # pragma: no cover
    psutil = None


_CURRENT_SESSION = contextvars.ContextVar("actigraphy_diagnostic_session", default=None)
_CURRENT_STAGE = contextvars.ContextVar("actigraphy_diagnostic_stage", default=None)

_TRACEBACK_LIMIT = int(os.getenv("DIAGNOSTIC_TRACEBACK_CHARS", "12000"))
_SUPPRESSED_LIMIT = int(os.getenv("DIAGNOSTIC_SUPPRESSED_ERROR_LIMIT", "30"))
_HASH_LIMIT_MB = float(os.getenv("DIAGNOSTIC_SHA256_MAX_MB", "512"))
_LOGGER = logging.getLogger("actigraphy.diagnostics")


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _round(value: Any, digits: int = 3):
    try:
        number = float(value)
        return round(number, digits) if math.isfinite(number) else None
    except Exception:
        return None


def _safe_text(value: Any, limit: int = 4000) -> str:
    try:
        text = str(value)
    except Exception:
        text = repr(value)
    return text[-limit:]


def _json_safe(value: Any, depth: int = 0):
    if depth > 8:
        return _safe_text(value, 500)
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, (datetime, pd.Timestamp)):
        return value.isoformat()
    if isinstance(value, pd.Timedelta):
        return str(value)
    if isinstance(value, dict):
        return {str(key): _json_safe(item, depth + 1) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_json_safe(item, depth + 1) for item in value]
    try:
        if hasattr(value, "item"):
            return _json_safe(value.item(), depth + 1)
    except Exception:
        pass
    if isinstance(value, pd.Series):
        return {"type": "Series", "rows": int(len(value)), "name": str(value.name) if value.name is not None else None}
    if isinstance(value, pd.DataFrame):
        return {"type": "DataFrame", "shape": list(value.shape), "columns": [str(c) for c in value.columns][:50]}
    return _safe_text(value, 2000)


def _traceback_text(exc: BaseException) -> str:
    try:
        text = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
    except Exception:
        text = traceback.format_exc()
    # Temporary upload paths are not useful to end users and can be noisy.
    text = text.replace("/tmp/", "<tmp>/")
    return text[-_TRACEBACK_LIMIT:]


def memory_snapshot() -> Dict[str, Any]:
    payload: Dict[str, Any] = {}
    try:
        if psutil is not None:
            proc = psutil.Process(os.getpid())
            info = proc.memory_info()
            payload.update({
                "rss_mb": _round(info.rss / (1024 ** 2), 2),
                "vms_mb": _round(info.vms / (1024 ** 2), 2),
                "process_percent": _round(proc.memory_percent(), 2),
            })
            virtual = psutil.virtual_memory()
            payload.update({
                "system_total_mb": _round(virtual.total / (1024 ** 2), 1),
                "system_available_mb": _round(virtual.available / (1024 ** 2), 1),
                "system_percent": _round(virtual.percent, 1),
            })
    except Exception:
        pass

    try:
        peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        # Linux reports KiB; macOS reports bytes.
        peak_mb = peak / (1024 ** 2) if sys.platform == "darwin" else peak / 1024
        payload["peak_rss_mb"] = _round(peak_mb, 2)
    except Exception:
        pass
    return payload


def disk_snapshot(path: str = "/tmp") -> Dict[str, Any]:
    try:
        usage = shutil.disk_usage(path)
        return {
            "path": path,
            "total_mb": _round(usage.total / (1024 ** 2), 1),
            "used_mb": _round(usage.used / (1024 ** 2), 1),
            "free_mb": _round(usage.free / (1024 ** 2), 1),
            "used_percent": _round((usage.used / usage.total) * 100.0 if usage.total else 0, 1),
        }
    except Exception as exc:
        return {"path": path, "error": _safe_text(exc)}


def _package_versions() -> Dict[str, str]:
    versions: Dict[str, str] = {}
    for package in [
        "fastapi", "uvicorn", "numpy", "pandas", "scipy", "numba",
        "pyActigraphy", "accelerometer", "pygt3x", "agcounts", "psutil",
    ]:
        try:
            versions[package] = importlib.metadata.version(package)
        except Exception:
            continue
    return versions


def environment_summary() -> Dict[str, Any]:
    return {
        "app_version": os.getenv("APP_VERSION", "local-dev"),
        "git_commit": os.getenv("GIT_COMMIT", "unknown"),
        "python": platform.python_version(),
        "platform": platform.platform(),
        "pid": os.getpid(),
        "packages": _package_versions(),
        "memory": memory_snapshot(),
        "temp_disk": disk_snapshot("/tmp"),
        "limits": {
            "max_server_side_bin_mb": os.getenv("MAX_SERVER_SIDE_BIN_MB"),
            "accelerometer_timeout_seconds": os.getenv("ACCELEROMETER_TIMEOUT_SECONDS"),
            "accelerometer_java_heap_mb": os.getenv("ACCELEROMETER_JAVA_HEAP_MB"),
        },
    }


def sha256_file(path: str, max_mb: float = _HASH_LIMIT_MB) -> Optional[str]:
    try:
        file_path = Path(path)
        if file_path.stat().st_size > max_mb * 1024 * 1024:
            return None
        digest = hashlib.sha256()
        with file_path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()
    except Exception:
        return None


def uploaded_file_summary(path: str, original_name: Optional[str] = None, content_type: Optional[str] = None) -> Dict[str, Any]:
    file_path = Path(path)
    try:
        size_bytes = file_path.stat().st_size
    except Exception:
        size_bytes = None
    digest = sha256_file(path)
    return {
        "file_name": original_name or file_path.name,
        "extension": Path(original_name or file_path.name).suffix.lower(),
        "content_type": content_type,
        "size_bytes": size_bytes,
        "size_mb": _round(size_bytes / (1024 ** 2), 3) if size_bytes is not None else None,
        "sha256": digest,
        "sha256_status": "calculated" if digest else ("skipped_or_unavailable" if size_bytes is not None else "unavailable"),
    }


def _index_summary(index: Any) -> Dict[str, Any]:
    payload: Dict[str, Any] = {"type": type(index).__name__}
    try:
        payload["rows"] = int(len(index))
    except Exception:
        return payload
    if not isinstance(index, pd.DatetimeIndex) or len(index) == 0:
        return payload
    try:
        payload.update({
            "start": index.min().isoformat(),
            "end": index.max().isoformat(),
            "timezone": str(index.tz) if index.tz is not None else None,
            "monotonic_increasing": bool(index.is_monotonic_increasing),
            "duplicate_timestamps": int(index.duplicated().sum()),
        })
        diffs = index.to_series().diff().dropna()
        if len(diffs):
            median = diffs.median()
            payload.update({
                "median_epoch_seconds": _round(median.total_seconds(), 4),
                "min_epoch_seconds": _round(diffs.min().total_seconds(), 4),
                "max_epoch_seconds": _round(diffs.max().total_seconds(), 4),
                "gap_count_over_1_5x_median": int((diffs > median * 1.5).sum()) if median > pd.Timedelta(0) else 0,
            })
    except Exception as exc:
        payload["inspection_error"] = _safe_text(exc)
    return payload


def _numeric_series_summary(series: Any) -> Dict[str, Any]:
    try:
        if isinstance(series, pd.DataFrame):
            numeric = series.select_dtypes(include="number")
            if numeric.empty:
                return {"available": False, "reason": "no_numeric_columns"}
            series = numeric.iloc[:, 0]
        if not isinstance(series, pd.Series):
            series = pd.Series(series)
        values = pd.to_numeric(series, errors="coerce")
        valid = values.dropna()
        total = int(len(values))
        return {
            "available": True,
            "name": str(getattr(series, "name", "") or ""),
            "rows": total,
            "valid_rows": int(len(valid)),
            "missing_rows": int(values.isna().sum()),
            "missing_percent": _round(values.isna().mean() * 100.0 if total else 0, 3),
            "zero_fraction": _round((valid == 0).mean() if len(valid) else None, 5),
            "negative_fraction": _round((valid < 0).mean() if len(valid) else None, 5),
            "min": _round(valid.min(), 6) if len(valid) else None,
            "max": _round(valid.max(), 6) if len(valid) else None,
            "mean": _round(valid.mean(), 6) if len(valid) else None,
            "std": _round(valid.std(), 6) if len(valid) else None,
        }
    except Exception as exc:
        return {"available": False, "inspection_error": _safe_text(exc)}


def raw_recording_summary(raw: Any) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "class": type(raw).__name__,
        "module": type(raw).__module__,
        "format": _safe_text(getattr(raw, "format", None), 300) if getattr(raw, "format", None) is not None else None,
        "name": _safe_text(getattr(raw, "name", None), 300) if getattr(raw, "name", None) is not None else None,
        "uuid": _safe_text(getattr(raw, "uuid", None), 300) if getattr(raw, "uuid", None) is not None else None,
    }
    data = getattr(raw, "data", None)
    if data is None:
        payload["data"] = {"available": False}
    else:
        payload["data"] = {
            "available": True,
            "container": type(data).__name__,
            "shape": list(data.shape) if hasattr(data, "shape") else None,
            "columns": [str(c) for c in data.columns] if isinstance(data, pd.DataFrame) else [str(getattr(data, "name", "activity") or "activity")],
            "index": _index_summary(getattr(data, "index", [])),
            "activity": _numeric_series_summary(data),
        }

    light = getattr(raw, "light", None)
    channels = []
    if light is not None and hasattr(light, "get_channel_list"):
        try:
            channels = [str(item) for item in light.get_channel_list()]
        except Exception:
            channels = []
    payload["light"] = {"available": bool(channels), "channels": channels}

    metadata = getattr(raw, "metadata", None)
    if isinstance(metadata, dict):
        safe_meta = {}
        for key in ["pages_decoded", "samples_decoded", "resample_freq", "direct_geneactiv_reader", "light_channels"]:
            if key in metadata:
                safe_meta[key] = metadata[key]
        payload["reader_metadata"] = safe_meta
    for attr in ["_ui_accelerometer_summary", "_ui_source_format", "_ui_detected_time_column", "_ui_detected_activity_column", "_ui_detected_light_column"]:
        value = getattr(raw, attr, None)
        if value is not None:
            payload.setdefault("ui_reader_metadata", {})[attr] = value
    return payload


def result_summary(value: Any) -> Dict[str, Any]:
    if value is None:
        return {"available": False, "type": "NoneType"}
    payload = {"available": True, "type": type(value).__name__}
    try:
        if isinstance(value, pd.Series):
            payload.update({"rows": int(len(value)), "valid_rows": int(value.notna().sum())})
        elif isinstance(value, pd.DataFrame):
            payload.update({"shape": list(value.shape), "columns": [str(c) for c in value.columns][:30]})
        elif isinstance(value, dict):
            payload["keys"] = [str(k) for k in value.keys()][:50]
        elif isinstance(value, (list, tuple, set)):
            payload["items"] = int(len(value))
        elif isinstance(value, (int, float)):
            payload["value"] = _round(value, 6)
        else:
            payload["preview"] = _safe_text(value, 500)
    except Exception:
        pass
    return payload


class DiagnosticSession:
    def __init__(self, endpoint: str, source_file_name: Optional[str] = None):
        self.request_id = str(uuid.uuid4())
        self.endpoint = endpoint
        self.source_file_name = source_file_name
        self.started_at = _utc_now()
        self.started_perf = time.perf_counter()
        self.status = "running"
        self.error: Optional[Dict[str, Any]] = None
        self.input_file: Dict[str, Any] = {}
        self.recording: Dict[str, Any] = {}
        self.stages = []
        self.events = []
        self.environment = environment_summary()
        self._session_token = None

    def activate(self):
        self._session_token = _CURRENT_SESSION.set(self)
        return self

    def deactivate(self):
        if self._session_token is not None:
            try:
                _CURRENT_SESSION.reset(self._session_token)
            except Exception:
                pass
            self._session_token = None

    @contextmanager
    def stage(self, name: str, category: str = "pipeline", details: Optional[Dict[str, Any]] = None):
        stage = {
            "id": str(uuid.uuid4()),
            "name": name,
            "category": category,
            "status": "running",
            "started_at": _utc_now(),
            "details": details or {},
            "memory_before": memory_snapshot(),
            "suppressed_errors": [],
        }
        self.stages.append(stage)
        try:
            _LOGGER.info(json.dumps({
                "diagnostic_event": "stage_started",
                "request_id": self.request_id,
                "endpoint": self.endpoint,
                "source_file_name": self.source_file_name,
                "stage": name,
                "category": category,
                "memory": stage["memory_before"],
            }, default=str))
        except Exception:
            pass
        token = _CURRENT_STAGE.set(stage)
        started = time.perf_counter()
        try:
            yield stage
            if stage["status"] == "running":
                if stage["suppressed_errors"]:
                    stage["status"] = "warning"
                else:
                    stage["status"] = "passed"
        except Exception as exc:
            stage["status"] = "failed"
            stage["error"] = {
                "type": type(exc).__name__,
                "message": _safe_text(exc),
                "traceback": _traceback_text(exc),
            }
            raise
        finally:
            stage["finished_at"] = _utc_now()
            stage["duration_seconds"] = _round(time.perf_counter() - started, 4)
            stage["memory_after"] = memory_snapshot()
            before = stage.get("memory_before", {}).get("rss_mb")
            after = stage.get("memory_after", {}).get("rss_mb")
            if before is not None and after is not None:
                stage["rss_change_mb"] = _round(after - before, 2)
            try:
                _LOGGER.info(json.dumps({
                    "diagnostic_event": "stage_finished",
                    "request_id": self.request_id,
                    "endpoint": self.endpoint,
                    "source_file_name": self.source_file_name,
                    "stage": name,
                    "category": category,
                    "status": stage.get("status"),
                    "duration_seconds": stage.get("duration_seconds"),
                    "memory_after": stage.get("memory_after"),
                    "error": stage.get("error"),
                    "suppressed_error_count": len(stage.get("suppressed_errors") or []),
                }, default=str))
            except Exception:
                pass
            try:
                _CURRENT_STAGE.reset(token)
            except Exception:
                pass

    def finish(self, status: str = "completed", exc: Optional[BaseException] = None):
        self.status = status
        if exc is not None:
            self.error = {
                "type": type(exc).__name__,
                "message": _safe_text(exc),
                "traceback": _traceback_text(exc),
            }
        try:
            _LOGGER.info(json.dumps({
                "diagnostic_event": "request_finished",
                "request_id": self.request_id,
                "endpoint": self.endpoint,
                "source_file_name": self.source_file_name,
                "status": status,
                "error": self.error,
                "duration_seconds": _round(time.perf_counter() - self.started_perf, 4),
                "memory": memory_snapshot(),
            }, default=str))
        except Exception:
            pass

    def payload(self) -> Dict[str, Any]:
        finished_at = _utc_now()
        payload = {
            "schema_version": "1.0",
            "request_id": self.request_id,
            "endpoint": self.endpoint,
            "source_file_name": self.source_file_name,
            "status": self.status,
            "started_at": self.started_at,
            "finished_at": finished_at,
            "total_duration_seconds": _round(time.perf_counter() - self.started_perf, 4),
            "error": self.error,
            "input_file": self.input_file,
            "recording": self.recording,
            "stages": self.stages,
            "events": self.events,
            "environment": {
                **self.environment,
                "memory_at_response": memory_snapshot(),
                "temp_disk_at_response": disk_snapshot("/tmp"),
            },
        }
        return _json_safe(payload)


def current_session() -> Optional[DiagnosticSession]:
    return _CURRENT_SESSION.get()


@contextmanager
def diagnostic_stage(name: str, category: str = "pipeline", details: Optional[Dict[str, Any]] = None):
    session = current_session()
    if session is None:
        yield {}
        return
    with session.stage(name=name, category=category, details=details) as stage:
        yield stage


def update_current_stage(**updates):
    stage = _CURRENT_STAGE.get()
    if not isinstance(stage, dict):
        return
    try:
        details = stage.setdefault("details", {})
        details.update(updates)
    except Exception:
        pass


def mark_current_stage(status: str, **updates):
    stage = _CURRENT_STAGE.get()
    if not isinstance(stage, dict):
        return
    try:
        stage["status"] = status
        if updates:
            stage.setdefault("details", {}).update(updates)
    except Exception:
        pass



def record_diagnostic_event(event_type: str, **details):
    session = current_session()
    stage = _CURRENT_STAGE.get()
    payload = {
        "type": event_type,
        "at": _utc_now(),
        "stage": stage.get("name") if isinstance(stage, dict) else None,
        "details": details,
        "memory": memory_snapshot(),
    }
    if session is not None and len(session.events) < 200:
        session.events.append(payload)
    try:
        _LOGGER.info(json.dumps({
            "diagnostic_event": event_type,
            "request_id": session.request_id if session is not None else None,
            "endpoint": session.endpoint if session is not None else None,
            "source_file_name": session.source_file_name if session is not None else None,
            **payload,
        }, default=str))
    except Exception:
        pass


def record_suppressed_exception(operation: str, exc: BaseException, note: Optional[str] = None):
    session = current_session()
    stage = _CURRENT_STAGE.get()
    payload = {
        "operation": operation,
        "type": type(exc).__name__,
        "message": _safe_text(exc),
        "note": note,
        "traceback": _traceback_text(exc),
        "at": _utc_now(),
    }
    if isinstance(stage, dict):
        errors = stage.setdefault("suppressed_errors", [])
        if len(errors) < _SUPPRESSED_LIMIT:
            errors.append(payload)
    elif session is not None and len(session.events) < _SUPPRESSED_LIMIT:
        session.events.append({"type": "suppressed_exception", **payload})
