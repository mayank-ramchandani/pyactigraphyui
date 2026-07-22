"""Small persistent job registry for work that must outlive an HTTP request.

Azure Container Apps HTTP ingress closes requests after 240 seconds.  Large
actigraphy uploads are therefore accepted first and their CPU-heavy preview or
analysis is run by a bounded background executor.  Job metadata and results
are mirrored to ``APP_DATA_DIR`` so status polling does not depend only on
process memory.

This is intentionally a single-container queue.  Production deployments must
keep at least one replica alive.  Deployments that use multiple replicas should
place ``APP_DATA_DIR`` on shared storage or replace this executor with a durable
external queue/Container Apps Job.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import shutil
import threading
import time
import traceback
from typing import Any, Callable, Dict, Optional, Tuple
import uuid

from .diagnostics import make_json_safe


_JOB_ID_RE = re.compile(r"^[A-Za-z0-9_-]{8,128}$")
_LOCK = threading.RLock()
_EXECUTOR = ThreadPoolExecutor(
    max_workers=max(1, int(os.getenv("ANALYSIS_JOB_MAX_WORKERS", "1"))),
    thread_name_prefix="actigraphy-job",
)
_TTL_SECONDS = max(300, int(os.getenv("ANALYSIS_JOB_TTL_SECONDS", "21600")))


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _jobs_root() -> Path:
    root = Path(os.getenv("APP_DATA_DIR", "/tmp/actigraphy-ui-data")) / "jobs"
    root.mkdir(parents=True, exist_ok=True)
    return root


def _normalise_job_id(value: Optional[str] = None) -> str:
    candidate = str(value or "").strip()
    if candidate and _JOB_ID_RE.fullmatch(candidate):
        return candidate
    return str(uuid.uuid4())


def _job_dir(job_id: str) -> Path:
    if not _JOB_ID_RE.fullmatch(str(job_id or "")):
        raise ValueError("Invalid job ID.")
    return _jobs_root() / str(job_id)


def _atomic_json_write(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(
        json.dumps(
            make_json_safe(payload),
            ensure_ascii=False,
            default=str,
            allow_nan=False,
        ),
        encoding="utf-8",
    )
    tmp.replace(path)


def _read_json(path: Path) -> Optional[Dict[str, Any]]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return payload if isinstance(payload, dict) else None
    except Exception:
        return None


def _cleanup_expired_jobs() -> None:
    cutoff = time.time() - _TTL_SECONDS
    root = _jobs_root().resolve()
    for candidate in list(root.iterdir()):
        if not candidate.is_dir():
            continue
        try:
            resolved = candidate.resolve()
            if resolved.parent != root:
                continue
            record = _read_json(resolved / "job.json") or {}
            updated_epoch = float(record.get("updated_epoch", resolved.stat().st_mtime))
            if updated_epoch < cutoff and record.get("status") not in {"queued", "running"}:
                shutil.rmtree(resolved)
        except Exception:
            continue


def create_job_record(
    job_type: str,
    *,
    requested_job_id: Optional[str] = None,
    request_id: Optional[str] = None,
    source_file_name: Optional[str] = None,
) -> Tuple[str, Path]:
    """Create a queued job and return its public ID and private directory."""
    with _LOCK:
        _cleanup_expired_jobs()
        job_id = _normalise_job_id(requested_job_id)
        directory = _job_dir(job_id)
        if directory.exists():
            job_id = str(uuid.uuid4())
            directory = _job_dir(job_id)
        (directory / "inputs").mkdir(parents=True, exist_ok=False)
        now = _utc_now()
        record = {
            "job_id": job_id,
            "request_id": str(request_id or job_id),
            "job_type": str(job_type),
            "source_file_name": source_file_name,
            "status": "queued",
            "message": "Upload accepted; waiting for a processing worker.",
            "created_at": now,
            "updated_at": now,
            "updated_epoch": time.time(),
            "started_at": None,
            "finished_at": None,
            "result_available": False,
        }
        _atomic_json_write(directory / "job.json", record)
        return job_id, directory


def update_job(job_id: str, **updates: Any) -> Dict[str, Any]:
    with _LOCK:
        directory = _job_dir(job_id)
        path = directory / "job.json"
        record = _read_json(path)
        if record is None:
            raise FileNotFoundError(f"Job does not exist: {job_id}")
        record.update(updates)
        record["updated_at"] = _utc_now()
        record["updated_epoch"] = time.time()
        _atomic_json_write(path, record)
        return record


def get_job(job_id: str) -> Optional[Dict[str, Any]]:
    try:
        record = _read_json(_job_dir(job_id) / "job.json")
    except ValueError:
        return None
    if record is None:
        return None
    return {key: value for key, value in record.items() if key != "updated_epoch"}


def get_job_result(job_id: str) -> Optional[Dict[str, Any]]:
    try:
        return _read_json(_job_dir(job_id) / "result.json")
    except ValueError:
        return None


def _remove_job_inputs(job_id: str) -> None:
    """Delete only the validated per-job input directory after processing."""
    try:
        directory = _job_dir(job_id).resolve()
        root = _jobs_root().resolve()
        inputs = (directory / "inputs").resolve()
        if directory.parent == root and inputs.parent == directory and inputs.exists():
            shutil.rmtree(inputs)
    except Exception:
        pass


def _run_job(job_id: str, worker: Callable[[], Dict[str, Any]]) -> None:
    update_job(
        job_id,
        status="running",
        message="Processing the uploaded recording.",
        started_at=_utc_now(),
    )
    try:
        outcome = worker()
        if not isinstance(outcome, dict):
            raise TypeError("Background worker did not return a result dictionary.")
        result_http_status = int(outcome.get("http_status", 200))
        result_content = outcome.get("content", {})
        _atomic_json_write(
            _job_dir(job_id) / "result.json",
            {"http_status": result_http_status, "content": result_content},
        )
        succeeded = 200 <= result_http_status < 400
        update_job(
            job_id,
            status="completed" if succeeded else "failed",
            message="Processing complete." if succeeded else "Processing returned an error.",
            finished_at=_utc_now(),
            result_available=True,
            result_http_status=result_http_status,
        )
    except Exception as exc:
        error_content = {
            "detail": f"Background processing failed: {exc}",
            "error_type": type(exc).__name__,
            "traceback": "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))[-12000:],
        }
        _atomic_json_write(
            _job_dir(job_id) / "result.json",
            {"http_status": 500, "content": error_content},
        )
        update_job(
            job_id,
            status="failed",
            message=str(exc)[:1000],
            finished_at=_utc_now(),
            result_available=True,
            result_http_status=500,
        )
    finally:
        _remove_job_inputs(job_id)


def submit_job(job_id: str, worker: Callable[[], Dict[str, Any]]) -> None:
    """Submit a previously-created job to the bounded executor."""
    _EXECUTOR.submit(_run_job, job_id, worker)
