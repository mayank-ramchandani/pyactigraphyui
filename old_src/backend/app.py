from typing import Optional, List
from fastapi import FastAPI, UploadFile, File, Form, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.datastructures import Headers
import json
import os
import tempfile
from pathlib import Path
from datetime import datetime, timezone
import uuid
import logging
import re

from pydantic import BaseModel, Field

from .activity_mapping import normalize_activity_mapping, raw_mapping_metadata
from .analysis import (
    run_basic_pyactigraphy_analysis,
    build_native_preview,
    build_light_preview,
    run_basic_pylight_analysis,
    get_basic_light_channels,
    build_light_rgb_preview,
    manipulate_light_data,
)
from .qc import quick_qc
from .data_quality import apply_data_quality_control
from .io_helpers import (
    build_baseraw_from_dataframe,
    detect_csv_mapping,
    detect_text_encoding,
    infer_reader_type,
    load_auto_tabular,
    load_custom_tabular,
    load_native_file,
    read_tabular_file,
    tabular_guidance,
)

from .accelerometer_loader import (
    convert_bin_lightweight_summary,
    summarize_uploaded_accelerometer_csv,
    MAX_SERVER_SIDE_BIN_MB,
    DEFAULT_JAVA_HEAP_MB,
)
from .gt3x_loader import summarize_gt3x_file, DEFAULT_GT3X_ACTIVITY_MODE

from .progress import get_progress
from .job_manager import (
    create_job_record,
    get_job,
    get_job_result,
    job_runtime_info,
    submit_job,
    update_job,
)

from .diagnostics import (
    DiagnosticSession,
    mark_current_stage,
    make_json_safe,
    raw_recording_summary,
    record_suppressed_exception,
    update_current_stage,
    uploaded_file_summary,
)



class FeedbackPayload(BaseModel):
    category: str = Field(default="issue", max_length=80)
    message: str = Field(..., min_length=1, max_length=8000)
    email: Optional[str] = Field(default=None, max_length=320)
    user_id: Optional[str] = Field(default=None, max_length=128)
    user_email: Optional[str] = Field(default=None, max_length=320)
    current_step: Optional[str] = Field(default=None, max_length=32)
    file_name: Optional[str] = Field(default=None, max_length=512)
    file_type: Optional[str] = Field(default=None, max_length=32)
    file_size_mb: Optional[float] = None
    endpoint: Optional[str] = Field(default=None, max_length=256)
    error_message: Optional[str] = Field(default=None, max_length=4000)
    app_version: Optional[str] = Field(default=None, max_length=128)
    backend_url: Optional[str] = Field(default=None, max_length=512)
    browser_info: Optional[str] = Field(default=None, max_length=1000)


def _get_data_dir() -> Path:
    data_dir = Path(os.getenv("APP_DATA_DIR", "/tmp/actigraphy-ui-data"))
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


def _append_jsonl(filename: str, payload: dict) -> Path:
    path = _get_data_dir() / filename
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False, default=str) + "\n")
    return path

app = FastAPI()


@app.exception_handler(Exception)
async def unhandled_server_exception(request: Request, exc: Exception):
    """Keep unexpected backend failures machine-readable during debugging.

    Process termination, ingress timeouts, and container OOM kills cannot be
    caught here, but ordinary Python and response-serialization exceptions can.
    """
    logging.getLogger("actigraphy.unhandled").exception(
        "Unhandled backend exception for %s", request.url.path
    )
    expose_details = os.getenv("EXPOSE_SERVER_ERROR_DETAILS", "true").strip().lower() in {
        "1", "true", "yes", "on"
    }
    return JSONResponse(
        status_code=500,
        content=make_json_safe({
            "ok": False,
            "detail": (
                f"Unhandled server error: {exc}"
                if expose_details
                else "An unexpected server error occurred. Check the backend logs."
            ),
            "error_type": type(exc).__name__,
            "endpoint": request.url.path,
        }),
    )


_default_cors_origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "https://actigraphy-ui.vercel.app",
    "https://da-cc-ca-pyactigraphy-web-prod.ambitiousdune-1d61e5e0.canadacentral.azurecontainerapps.io"
]
_extra_cors_origins = [
    origin.strip()
    for origin in os.getenv("CORS_ALLOW_ORIGINS", "").split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_default_cors_origins + _extra_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/version")
def version():
    return {
        "ok": True,
        "app_version": os.getenv("APP_VERSION", "local-dev"),
        "git_commit": os.getenv("GIT_COMMIT", "unknown"),
        "features": {
            "feedback": True,
            "gt3x_pygt3x": True,
            "gt3x_streaming_epoch_loader": True,
            "background_preview_analysis_jobs": True,
            "strict_preview_json": True,
            "resilient_background_job_polling": True,
            "bin_cwa_accelerometer": True,
            "saved_runs_frontend_supabase": True,
            "structured_diagnostics": True,
            "json_safe_metric_results": True,
            "live_analysis_progress": True,
            "geneactiv_ra_average_daily_profile": True,
            "geneactiv_pyactigraphy_aot": True,
            "accelerometer_acc_default": True,
            "preview_analysis_mapping_decoupled": True,
            "documentation_center": True,
            "generic_csv_mapping": True,
            "localized_rpx_csv": True,
            "tabular_column_inspection": True,
            "missingness_nonwear_valid_day_qc": True,
            "background_light_preview_jobs": True,
            "gt3x_light_content_detection": True,
            "gt3x_streaming_lux_extraction": True,
            "background_light_analysis_jobs": True,
        },
        "runtime": job_runtime_info(),
    }




@app.get("/api/progress/{request_id}")
def analysis_progress(request_id: str):
    payload = get_progress(request_id)
    if payload is None:
        return JSONResponse(status_code=404, content={"ok": False, "detail": "Progress is not available yet."})
    return {"ok": True, **payload}

@app.post("/api/feedback")
async def submit_feedback(payload: FeedbackPayload):
    try:
        record = payload.model_dump()
    except AttributeError:
        # Pydantic v1 fallback.
        record = payload.dict()

    record.update({
        "id": str(uuid.uuid4()),
        "created_at": datetime.now(timezone.utc).isoformat(),
    })

    path = _append_jsonl("feedback.jsonl", record)
    return {"ok": True, "id": record["id"], "stored": str(path)}


def _write_upload_to_temp(upload: UploadFile):
    suffix = Path(upload.filename or "upload").suffix.lower()
    bytes_written = 0
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        while True:
            chunk = upload.file.read(1024 * 1024)
            if not chunk:
                break
            tmp.write(chunk)
            bytes_written += len(chunk)
        update_current_stage(
            uploaded_file_name=upload.filename,
            uploaded_content_type=upload.content_type,
            bytes_written=bytes_written,
            size_mb=round(bytes_written / (1024 * 1024), 3),
        )
        return tmp.name


def _safe_job_input_name(filename: Optional[str], prefix: str) -> str:
    basename = Path(filename or "upload").name
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", basename).strip("._") or "upload"
    return f"{prefix}-{cleaned}"[:240]


def _write_upload_to_job(upload: UploadFile, job_dir: Path, prefix: str) -> dict:
    """Persist an upload before its request-scoped UploadFile is closed."""
    target = job_dir / "inputs" / _safe_job_input_name(upload.filename, prefix)
    bytes_written = 0
    upload.file.seek(0)
    with target.open("wb") as handle:
        while True:
            chunk = upload.file.read(1024 * 1024)
            if not chunk:
                break
            handle.write(chunk)
            bytes_written += len(chunk)
    return {
        "path": str(target),
        "filename": upload.filename or target.name,
        "content_type": upload.content_type,
        "size_bytes": bytes_written,
    }


def _uploads_from_job_specs(specs):
    """Open stored job inputs as UploadFile objects for existing route logic."""
    opened = []
    uploads = []
    for spec in specs or []:
        handle = open(spec["path"], "rb")
        opened.append(handle)
        uploads.append(
            UploadFile(
                file=handle,
                filename=spec.get("filename"),
                headers=Headers({"content-type": spec.get("content_type") or "application/octet-stream"}),
            )
        )
    return uploads, opened


def _response_outcome(response) -> dict:
    status_code = int(getattr(response, "status_code", 200))
    body = getattr(response, "body", b"")
    if isinstance(body, bytes):
        body = body.decode("utf-8", errors="replace")
    try:
        content = json.loads(body) if body else {}
    except Exception:
        content = {"detail": str(body)[:4000]}
    return {"http_status": status_code, "content": content}


def _cleanup_temp_paths(paths):
    removed = 0
    errors = []
    for path in paths or []:
        if not path:
            continue
        try:
            os.remove(path)
            removed += 1
        except FileNotFoundError:
            continue
        except Exception as exc:
            errors.append(str(exc))
    return {"removed": removed, "errors": errors[:10]}


def _persist_diagnostics(payload):
    try:
        max_mb = float(os.getenv("DIAGNOSTIC_LOG_MAX_MB", "50"))
        path = _get_data_dir() / "diagnostics.jsonl"
        if path.exists() and path.stat().st_size > max_mb * 1024 * 1024:
            rotated = path.with_suffix(".jsonl.1")
            try:
                rotated.unlink(missing_ok=True)
            except TypeError:
                if rotated.exists():
                    rotated.unlink()
            path.replace(rotated)
        _append_jsonl("diagnostics.jsonl", payload)
    except Exception:
        logging.getLogger("actigraphy.diagnostics").exception("Could not persist diagnostic payload")


def _json_or_empty(value):
    try:
        return json.loads(value or "{}")
    except Exception:
        return {}


def _safe_json_response(status_code: int, content):
    """Return JSON even when a metric produced a NumPy/Pandas object.

    JSONResponse serializes content in its constructor, which occurs after the
    endpoint's main try/except block. Sanitizing here prevents an otherwise
    successful analysis from becoming an opaque plain-text HTTP 500.
    """
    request_id = None
    try:
        if isinstance(content, dict):
            request_id = (content.get("diagnostics") or {}).get("request_id")
        safe_content = make_json_safe(content)
        return JSONResponse(status_code=status_code, content=safe_content)
    except Exception as exc:
        logging.getLogger("actigraphy.response").exception("Could not serialize API response")
        return JSONResponse(
            status_code=500,
            content={
                "ok": False,
                "detail": "The analysis completed, but the server could not serialize the response.",
                "error_type": type(exc).__name__,
                "error_message": str(exc),
                "request_id": request_id,
            },
        )


NO_LIGHT_MEASUREMENTS_DETAIL = (
    "This file was inspected, but no embedded light measurements were found. "
    "Light preview and light metrics were skipped; activity preview and analysis remain available."
)


def _validate_light_upload_format(upload: UploadFile) -> None:
    """Retained for compatibility; light capability is determined from content."""
    if upload is None:
        raise ValueError("Select a file to inspect for embedded light measurements.")


def _clean_csv_mapping(value) -> dict:
    # FastAPI Form defaults remain Param objects when route functions are called
    # directly in unit tests/background helpers rather than through dependency
    # injection. Resolve their declared default before parsing.
    if not isinstance(value, (str, dict)) and hasattr(value, "default"):
        value = value.default
    mapping = _json_or_empty(value) if isinstance(value, str) else (value or {})
    if not isinstance(mapping, dict):
        raise ValueError("csvMapping must be a JSON object.")
    allowed = {
        "timestamp_col", "time_col", "activity_col", "light_col",
        "temperature_col", "nonwear_col",
    }
    return {
        key: str(mapping.get(key) or "").strip()
        for key in allowed
        if str(mapping.get(key) or "").strip()
    }


def _load_native_supported_file(
    file_path: str,
    activity_mapping: str = "auto",
    purpose: str = "activity",
    csv_mapping=None,
    csv_separator: str = ",",
):
    """Load native recordings and mapped tabular files through one path."""
    if not isinstance(csv_separator, str) and hasattr(csv_separator, "default"):
        csv_separator = csv_separator.default
    csv_separator = str(csv_separator or ",")
    reader_type = infer_reader_type(file_path)

    if reader_type == "tabular":
        requested_mapping = normalize_activity_mapping(activity_mapping)
        if requested_mapping not in {"auto", "original"}:
            raise ValueError(
                f"{requested_mapping.upper()} cannot be calculated from a generic mapped activity column. "
                "Choose Recommended/Source activity, or upload raw tri-axial .bin/.cwa/.gt3x data."
            )

        mapping = _clean_csv_mapping(csv_mapping)
        require_activity = str(purpose or "activity").strip().lower() != "light"
        if mapping.get("timestamp_col"):
            dataframe = load_custom_tabular(
                file_path=file_path,
                timestamp_col=mapping["timestamp_col"],
                time_col=mapping.get("time_col"),
                activity_col=mapping.get("activity_col"),
                light_col=mapping.get("light_col"),
                temperature_col=mapping.get("temperature_col"),
                nonwear_col=mapping.get("nonwear_col"),
                sep=csv_separator or ",",
                require_activity=require_activity,
            )
        else:
            dataframe, mapping = load_auto_tabular(
                file_path,
                sep=csv_separator or ",",
                require_activity=require_activity,
            )

        raw = build_baseraw_from_dataframe(
            dataframe,
            name=Path(file_path).name,
            uuid=f"mapped-{Path(file_path).stem}",
            require_activity=require_activity,
        )
        raw.metadata = {
            **(getattr(raw, "metadata", None) or {}),
            "detected_mapping": mapping,
        }
        return raw, "tabular_mapped"

    raw = load_native_file(
        file_path,
        reader_type,
        activity_mapping=activity_mapping,
        purpose=purpose,
    )
    return raw, reader_type


def _light_detection_payload(raw, reader_type: str) -> dict:
    channels_payload = get_basic_light_channels(raw)
    channels = channels_payload.get("channels") or []
    metadata = getattr(raw, "metadata", None) or {}
    gt3x_summary = metadata.get("gt3x_summary") if isinstance(metadata, dict) else None
    available = bool(channels)
    return {
        "inspected": True,
        "available": available,
        "status": "available" if available else "not_present",
        "message": (
            f"Embedded light data were found in {len(channels)} channel(s)."
            if available
            else NO_LIGHT_MEASUREMENTS_DETAIL
        ),
        "detected_input_type": reader_type,
        "channels": channels,
        "default_channel": channels_payload.get("default_channel"),
        "gt3x": (
            {
                "record_type": gt3x_summary.get("_gt3x_light_record_type"),
                "source_member": gt3x_summary.get("_gt3x_light_source_member"),
                "lux_records": gt3x_summary.get("_gt3x_lux_records"),
                "events_read": gt3x_summary.get("_gt3x_light_events_read"),
                "epoch_period_seconds": gt3x_summary.get("_gt3x_light_epoch_period_seconds"),
                "serial_number": gt3x_summary.get("serial_number"),
                "device": gt3x_summary.get("device"),
            }
            if isinstance(gt3x_summary, dict)
            else None
        ),
    }


@app.post("/api/accelerometer/convert-lite")
def convert_accelerometer_lite(
    file: UploadFile = File(...),
    epochPeriod: int = Form(30),
    javaHeapMb: Optional[int] = Form(DEFAULT_JAVA_HEAP_MB or 0),
    activityMapping: str = Form("auto"),
):
    """Diagnostic endpoint for raw .bin/.cwa/.gt3x files or uploaded timeSeries CSVs.

    This returns a compact summary rather than running the full pyActigraphy analysis.
    It is useful on low-memory Render instances to confirm that the conversion/loading path works.
    """
    tmp_path = None
    try:
        tmp_path = _write_upload_to_temp(file)
        requested_mapping = normalize_activity_mapping(activityMapping)
        suffix = Path(file.filename or tmp_path).suffix.lower()

        if suffix in (".bin", ".cwa"):
            payload = convert_bin_lightweight_summary(
                tmp_path,
                epoch_period=epochPeriod,
                java_heap_mb=javaHeapMb or None,
                activity_mapping=requested_mapping,
            )
            mode = "server_side_raw_bin_conversion"
        elif suffix == ".gt3x":
            payload = summarize_gt3x_file(
                tmp_path,
                epoch_period=epochPeriod,
                activity_mode=DEFAULT_GT3X_ACTIVITY_MODE,
                activity_mapping=requested_mapping,
            )
            mode = "server_side_gt3x_pygt3x"
        else:
            payload = summarize_uploaded_accelerometer_csv(tmp_path, epoch_period=epochPeriod, activity_mapping=requested_mapping)
            mode = "uploaded_accelerometer_timeseries_csv"

        return JSONResponse(
            content={
                "ok": True,
                "mode": mode,
                "max_server_side_bin_mb": MAX_SERVER_SIDE_BIN_MB,
                **payload,
            }
        )

    except ValueError as e:
        return JSONResponse(status_code=400, content={"ok": False, "detail": str(e)})
    except Exception as e:
        return JSONResponse(status_code=500, content={"ok": False, "detail": "Server error: {}".format(str(e))})
    finally:
        _cleanup_temp_paths([tmp_path])


@app.post("/api/tabular/columns")
def inspect_tabular_columns(
    file: UploadFile = File(...),
    csvSeparator: str = Form(","),
):
    """Inspect a CSV/text/spreadsheet upload for optional manual mapping."""
    tmp_path = None
    try:
        tmp_path = _write_upload_to_temp(file)
        reader_type = infer_reader_type(tmp_path)
        if reader_type not in {"tabular", "rpx", "tal", "mesa", "atr"}:
            raise ValueError(
                "Manual column mapping is intended for CSV, text, or spreadsheet uploads."
            )

        dataframe = read_tabular_file(tmp_path, sep=csvSeparator or ",")
        mapping = detect_csv_mapping(dataframe)
        guidance = tabular_guidance(dataframe)
        return _safe_json_response(
            status_code=200,
            content={
                "ok": True,
                "columns": [str(column) for column in dataframe.columns],
                "detected_mapping": mapping,
                "detected_input_type": reader_type,
                "source_encoding": (
                    dataframe.attrs.get("source_encoding")
                    or (detect_text_encoding(tmp_path) if Path(tmp_path).suffix.lower() in {".csv", ".txt", ".gz"} else None)
                ),
                "guidance": guidance,
            },
        )
    except ValueError as exc:
        return JSONResponse(status_code=400, content={"detail": str(exc)})
    except Exception as exc:
        return JSONResponse(status_code=500, content={"detail": f"Server error: {exc}"})
    finally:
        _cleanup_temp_paths([tmp_path])


@app.post("/api/preview/basic")
def preview_basic(
    file: UploadFile = File(...),
    activityChannel: str = Form("VM"),
    activityMapping: str = Form("auto"),
    resampleFreq: str = Form("1min"),
    csvMapping: str = Form("{}"),
    csvSeparator: str = Form(","),
    maskingFiles: Optional[List[UploadFile]] = File(None),
    sleepDiaryFiles: Optional[List[UploadFile]] = File(None),
    startStopFiles: Optional[List[UploadFile]] = File(None),
):
    tmp_path = None
    try:
        parsed_csv_mapping = _clean_csv_mapping(csvMapping)

        tmp_path = _write_upload_to_temp(file)
        requested_mapping = normalize_activity_mapping(activityMapping)
        raw, reader_type = _load_native_supported_file(
            tmp_path,
            activity_mapping=requested_mapping,
            csv_mapping=parsed_csv_mapping,
            csv_separator=csvSeparator,
        )
        mapping_details = raw_mapping_metadata(raw)

        preview = build_native_preview(
            raw=raw,
            activity_channel=activityChannel,
            resample_freq=resampleFreq,
        )

        return _safe_json_response(
            status_code=200,
            content={
                **preview,
                "detected_input_type": reader_type,
                "native_reader_used": reader_type != "tabular_mapped",
                "activity_mapping": mapping_details,
            }
        )

    except ValueError as e:
        return JSONResponse(status_code=400, content={"detail": str(e)})
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"detail": "Server error: {}".format(str(e))}
        )
    finally:
        _cleanup_temp_paths([tmp_path])


@app.post("/api/light/preview")
def preview_light(
    file: UploadFile = File(...),
    resampleFreq: str = Form("1min"),
    rgbResampleFreq: str = Form("5min"),
    csvMapping: str = Form("{}"),
    csvSeparator: str = Form(","),
    maskingFiles: Optional[List[UploadFile]] = File(None),
    sleepDiaryFiles: Optional[List[UploadFile]] = File(None),
    startStopFiles: Optional[List[UploadFile]] = File(None),
):
    tmp_path = None
    try:
        _validate_light_upload_format(file)
        parsed_csv_mapping = _clean_csv_mapping(csvMapping)

        tmp_path = _write_upload_to_temp(file)
        raw, reader_type = _load_native_supported_file(
            tmp_path,
            purpose="light",
            csv_mapping=parsed_csv_mapping,
            csv_separator=csvSeparator,
        )

        preview = build_light_preview(raw=raw, resample_freq=resampleFreq)
        detection = _light_detection_payload(raw, reader_type)

        if not preview.get("light_preview_available"):
            return _safe_json_response(
                status_code=200,
                content={
                    **preview,
                    "channels": [],
                    "default_channel": None,
                    "rgb_preview": [],
                    "rgb_summary": {},
                    "rgb_resample_freq": rgbResampleFreq,
                    "light_detection": detection,
                    "message": detection["message"],
                    "skipped": True,
                    "detected_input_type": reader_type,
                    "native_reader_used": reader_type != "tabular_mapped",
                },
            )

        channels_payload = get_basic_light_channels(raw)
        rgb_payload = build_light_rgb_preview(raw=raw, resample_freq=rgbResampleFreq)
        return _safe_json_response(
            status_code=200,
            content={
                **preview,
                **channels_payload,
                "rgb_preview": rgb_payload.get("rgb_preview", []),
                "rgb_summary": rgb_payload.get("rgb_summary", {}),
                "rgb_resample_freq": rgbResampleFreq,
                "light_detection": detection,
                "message": detection["message"],
                "skipped": False,
                "detected_input_type": reader_type,
                "native_reader_used": reader_type != "tabular_mapped",
            }
        )

    except ValueError as e:
        return JSONResponse(status_code=400, content={"detail": str(e)})
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"detail": "Server error: {}".format(str(e))}
        )
    finally:
        _cleanup_temp_paths([tmp_path])

@app.post("/api/light/rgb-preview")
def preview_light_rgb(
    file: UploadFile = File(...),
    resampleFreq: str = Form("5min"),
):
    tmp_path = None
    try:
        _validate_light_upload_format(file)
        tmp_path = _write_upload_to_temp(file)
        raw, reader_type = _load_native_supported_file(tmp_path, purpose="light")

        payload = build_light_rgb_preview(raw=raw, resample_freq=resampleFreq)
        detection = _light_detection_payload(raw, reader_type)

        return _safe_json_response(
            status_code=200,
            content={
                **payload,
                "light_detection": detection,
                "message": detection["message"],
                "skipped": not detection["available"],
                "detected_input_type": reader_type,
                "native_reader_used": reader_type != "tabular_mapped",
            }
        )

    except ValueError as e:
        return JSONResponse(status_code=400, content={"detail": str(e)})
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"detail": "Server error: {}".format(str(e))}
        )
    finally:
        _cleanup_temp_paths([tmp_path])

@app.post("/api/light/channels")
def light_channels(
    file: UploadFile = File(...),
):
    tmp_path = None
    try:
        _validate_light_upload_format(file)
        tmp_path = _write_upload_to_temp(file)
        raw, reader_type = _load_native_supported_file(tmp_path, purpose="light")

        payload = get_basic_light_channels(raw)
        detection = _light_detection_payload(raw, reader_type)

        return _safe_json_response(
            status_code=200,
            content={
                **payload,
                "light_detection": detection,
                "message": detection["message"],
                "skipped": not detection["available"],
                "detected_input_type": reader_type,
                "native_reader_used": reader_type != "tabular_mapped",
            }
        )

    except ValueError as e:
        return JSONResponse(status_code=400, content={"detail": str(e)})
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"detail": "Server error: {}".format(str(e))}
        )
    finally:
        _cleanup_temp_paths([tmp_path])


@app.post("/api/light/analyze")
def analyze_light(
    file: UploadFile = File(...),
    metricId: str = Form(...),
    channel: Optional[str] = Form(None),
    thresholdLux: Optional[str] = Form(None),
    startTime: Optional[str] = Form(None),
    stopTime: Optional[str] = Form(None),
    bins: str = Form("24h"),
    agg: str = Form("mean"),
    aggFuncs: str = Form(""),
    outputFormat: str = Form("minute"),
    lmxLength: str = Form("5h"),
    lowest: str = Form("true"),
    binarize: str = Form("false"),
    csvMapping: str = Form("{}"),
    csvSeparator: str = Form(","),
):
    session = DiagnosticSession("/api/light/analyze", source_file_name=file.filename).activate()
    temp_paths = []
    status_code = 200
    response_content = {}
    final_status = "completed"
    caught_exception = None

    try:
        _validate_light_upload_format(file)
        with session.stage("request.parse_light_metric", category="request"):
            parsed_csv_mapping = _clean_csv_mapping(csvMapping)
            agg_funcs = [x.strip() for x in aggFuncs.split(",") if x.strip()] if aggFuncs else None
            update_current_stage(
                metric_id=metricId,
                channel=channel or None,
                threshold_lux=thresholdLux,
                start_time=startTime,
                stop_time=stopTime,
                bins=bins,
                aggregation=agg,
                aggregation_functions=agg_funcs,
                output_format=outputFormat,
                lmx_length=lmxLength,
                lowest=str(lowest).lower() == "true",
                binarize=str(binarize).lower() == "true",
            )

        with session.stage("upload.primary_file", category="upload"):
            tmp_path = _write_upload_to_temp(file)
            temp_paths.append(tmp_path)
            session.input_file = uploaded_file_summary(tmp_path, file.filename, file.content_type)
            update_current_stage(**session.input_file)

        with session.stage("input.detect_reader", category="reader"):
            reader_type = infer_reader_type(tmp_path)
            update_current_stage(detected_input_type=reader_type)

        with session.stage("input.load_recording", category="reader", details={"detected_input_type": reader_type}):
            raw, reader_type = _load_native_supported_file(
                tmp_path,
                purpose="light",
                csv_mapping=parsed_csv_mapping,
                csv_separator=csvSeparator,
            )
            update_current_stage(raw_class=type(raw).__name__, raw_module=type(raw).__module__)

        with session.stage("input.inspect_recording", category="data_validation"):
            session.recording = raw_recording_summary(raw)
            update_current_stage(**session.recording)
            if not session.recording.get("light", {}).get("available"):
                detection = _light_detection_payload(raw, reader_type)
                response_content = {
                    "metric_id": metricId,
                    "result": None,
                    "skipped": True,
                    "light_available": False,
                    "light_detection": detection,
                    "message": detection["message"],
                    "detected_input_type": reader_type,
                    "native_reader_used": reader_type != "tabular_mapped",
                }
                final_status = "completed_with_warnings"
                mark_current_stage("warning")

        if session.recording.get("light", {}).get("available"):
            with session.stage(
                f"metric.light.{metricId}",
                category="light_metric",
                details={"metric_id": metricId, "channel": channel or None},
            ):
                payload = run_basic_pylight_analysis(
                    raw=raw,
                    metric_id=metricId,
                    channel=channel or None,
                    threshold_lux=thresholdLux,
                    start_time=startTime,
                    stop_time=stopTime,
                    bins=bins,
                    agg=agg,
                    agg_funcs=agg_funcs,
                    oformat=outputFormat,
                    lmx_length=lmxLength,
                    lowest=str(lowest).lower() == "true",
                    binarize=str(binarize).lower() == "true",
                )
                update_current_stage(result_kind=(payload.get("result") or {}).get("kind"), channel_used=payload.get("channel"))

            response_content = {
                **payload,
                "skipped": False,
                "light_available": True,
                "light_detection": _light_detection_payload(raw, reader_type),
                "detected_input_type": reader_type,
                "native_reader_used": reader_type != "tabular_mapped",
            }

    except ValueError as exc:
        caught_exception = exc
        final_status = "failed"
        status_code = 400
        response_content = {"detail": str(exc)}
    except Exception as exc:
        caught_exception = exc
        final_status = "failed"
        status_code = 500
        response_content = {"detail": "Server error: {}".format(str(exc))}
    finally:
        try:
            with session.stage("request.cleanup_temp_files", category="cleanup"):
                cleanup_summary = _cleanup_temp_paths(temp_paths)
                update_current_stage(**cleanup_summary)
                if cleanup_summary.get("errors"):
                    mark_current_stage("warning")
        except Exception:
            pass
        session.finish(final_status, caught_exception)
        diagnostics_payload = session.payload()
        response_content["diagnostics"] = diagnostics_payload
        _persist_diagnostics(diagnostics_payload)
        session.deactivate()

    return _safe_json_response(status_code=status_code, content=response_content)


@app.post("/api/light/analyze-batch")
def analyze_light_batch(
    file: UploadFile = File(...),
    metricIds: str = Form("[]"),
    channel: Optional[str] = Form(None),
    thresholdLux: Optional[str] = Form(None),
    startTime: Optional[str] = Form(None),
    stopTime: Optional[str] = Form(None),
    bins: str = Form("24h"),
    agg: str = Form("mean"),
    aggFuncs: str = Form(""),
    outputFormat: str = Form("minute"),
    lmxLength: str = Form("5h"),
    lowest: str = Form("true"),
    binarize: str = Form("false"),
    csvMapping: str = Form("{}"),
    csvSeparator: str = Form(","),
    requestId: Optional[str] = Form(None),
):
    """Inspect once and run all selected light metrics on one loaded recording."""
    session = DiagnosticSession(
        "/api/light/analyze-batch",
        source_file_name=file.filename,
        request_id=requestId,
    ).activate()
    temp_paths = []
    status_code = 200
    response_content = {}
    final_status = "completed"
    caught_exception = None

    try:
        with session.stage("request.parse_light_metrics", category="request"):
            parsed_csv_mapping = _clean_csv_mapping(csvMapping)
            try:
                parsed_metric_ids = json.loads(metricIds or "[]")
            except Exception as exc:
                raise ValueError("metricIds must be a JSON array of light metric identifiers.") from exc
            if not isinstance(parsed_metric_ids, list):
                raise ValueError("metricIds must be a JSON array of light metric identifiers.")
            selected_metric_ids = list(
                dict.fromkeys(str(item).strip() for item in parsed_metric_ids if str(item).strip())
            )
            if not selected_metric_ids:
                raise ValueError("Select at least one light metric.")
            agg_funcs = [item.strip() for item in aggFuncs.split(",") if item.strip()] or None
            session.set_expected_stage_total(4 + len(selected_metric_ids))
            update_current_stage(metric_ids=selected_metric_ids)

        with session.stage("upload.primary_file", category="upload"):
            tmp_path = _write_upload_to_temp(file)
            temp_paths.append(tmp_path)
            session.input_file = uploaded_file_summary(tmp_path, file.filename, file.content_type)
            update_current_stage(**session.input_file)

        with session.stage("input.detect_reader", category="reader"):
            reader_type = infer_reader_type(tmp_path)
            update_current_stage(detected_input_type=reader_type)

        with session.stage(
            "input.inspect_light",
            category="reader",
            details={"detected_input_type": reader_type},
        ):
            raw, reader_type = _load_native_supported_file(
                tmp_path,
                purpose="light",
                csv_mapping=parsed_csv_mapping,
                csv_separator=csvSeparator,
            )
            session.recording = raw_recording_summary(raw)
            detection = _light_detection_payload(raw, reader_type)
            update_current_stage(
                raw_class=type(raw).__name__,
                light_available=detection["available"],
                light_channels=detection["channels"],
            )
            if not detection["available"]:
                mark_current_stage("warning")

        results = {}
        metric_diagnostics = {}
        metric_errors = []

        if detection["available"]:
            for metric_id in selected_metric_ids:
                try:
                    with session.stage(
                        f"metric.light.{metric_id}",
                        category="light_metric",
                        details={"metric_id": metric_id, "channel": channel or None},
                    ):
                        payload = run_basic_pylight_analysis(
                            raw=raw,
                            metric_id=metric_id,
                            channel=channel or None,
                            threshold_lux=thresholdLux,
                            start_time=startTime,
                            stop_time=stopTime,
                            bins=bins,
                            agg=agg,
                            agg_funcs=agg_funcs,
                            oformat=outputFormat,
                            lmx_length=lmxLength,
                            lowest=str(lowest).lower() == "true",
                            binarize=str(binarize).lower() == "true",
                        )
                        results[metric_id] = payload
                        metric_diagnostics[metric_id] = {
                            "status": "completed",
                            "metric_id": metric_id,
                            "channel": payload.get("channel"),
                        }
                        update_current_stage(
                            result_kind=(payload.get("result") or {}).get("kind"),
                            channel_used=payload.get("channel"),
                        )
                except Exception as exc:
                    metric_errors.append(f"{metric_id}: {exc}")
                    metric_diagnostics[metric_id] = {
                        "status": "failed",
                        "metric_id": metric_id,
                        "message": str(exc),
                    }
                    final_status = "completed_with_warnings"
        else:
            final_status = "completed_with_warnings"
            metric_diagnostics = {
                metric_id: {
                    "status": "skipped",
                    "metric_id": metric_id,
                    "message": detection["message"],
                }
                for metric_id in selected_metric_ids
            }

        response_content = {
            "results": results,
            "metric_diagnostics": metric_diagnostics,
            "metric_errors": metric_errors,
            "light_available": detection["available"],
            "light_detection": detection,
            "skipped": not detection["available"],
            "message": (
                detection["message"]
                if not detection["available"]
                else (
                    "Some light metrics could not be calculated."
                    if metric_errors
                    else "Selected light metrics completed."
                )
            ),
            "detected_input_type": reader_type,
            "native_reader_used": reader_type != "tabular_mapped",
        }

    except ValueError as exc:
        caught_exception = exc
        final_status = "failed"
        status_code = 400
        response_content = {"detail": str(exc)}
    except Exception as exc:
        caught_exception = exc
        final_status = "failed"
        status_code = 500
        response_content = {"detail": f"Server error: {exc}"}
    finally:
        try:
            with session.stage("request.cleanup_temp_files", category="cleanup"):
                cleanup_summary = _cleanup_temp_paths(temp_paths)
                update_current_stage(**cleanup_summary)
                if cleanup_summary.get("errors"):
                    mark_current_stage("warning")
        except Exception:
            pass
        session.finish(final_status, caught_exception)
        diagnostics_payload = session.payload()
        response_content["diagnostics"] = diagnostics_payload
        _persist_diagnostics(diagnostics_payload)
        session.deactivate()

    return _safe_json_response(status_code=status_code, content=response_content)


@app.post("/api/light/manipulate")
def manipulate_light(
    file: UploadFile = File(...),
    channels: str = Form(""),
    truncateStart: Optional[str] = Form(None),
    truncateStop: Optional[str] = Form(None),
    dailyStartTime: Optional[str] = Form(None),
    dailyStopTime: Optional[str] = Form(None),
    resampleFreq: Optional[str] = Form(""),
    binarize: str = Form("false"),
    thresholdLux: Optional[str] = Form(None),
    filterMethod: str = Form("none"),
    filterWindow: str = Form("15min"),
):
    tmp_path = None
    try:
        _validate_light_upload_format(file)
        tmp_path = _write_upload_to_temp(file)
        raw, reader_type = _load_native_supported_file(tmp_path, purpose="light")

        selected_channels = [x.strip() for x in channels.split(",") if x.strip()] if channels else None

        payload = manipulate_light_data(
            raw=raw,
            channels=selected_channels,
            truncate_start=truncateStart or None,
            truncate_stop=truncateStop or None,
            daily_start_time=dailyStartTime or None,
            daily_stop_time=dailyStopTime or None,
            resample_freq=resampleFreq or None,
            binarize=str(binarize).lower() == "true",
            threshold_lux=thresholdLux,
            filter_method=filterMethod or "none",
            filter_window=filterWindow or "15min",
        )

        return JSONResponse(
            content={
                **payload,
                "detected_input_type": reader_type,
                "native_reader_used": reader_type != "tabular_mapped",
            }
        )

    except ValueError as e:
        return JSONResponse(status_code=400, content={"detail": str(e)})
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"detail": "Server error: {}".format(str(e))}
        )
    finally:
        _cleanup_temp_paths([tmp_path])



def _read_support_table(file_path: str):
    try:
        if file_path.lower().endswith((".xls", ".xlsx")):
            import pandas as pd
            return pd.read_excel(file_path)
        import pandas as pd
        return pd.read_csv(file_path)
    except Exception:
        try:
            import pandas as pd
            return pd.read_csv(file_path, sep=None, engine="python")
        except Exception:
            return None


def _find_column(df, candidates):
    if df is None:
        return None
    lookup = {str(c).strip().lower(): c for c in df.columns}
    for candidate in candidates:
        if candidate.lower() in lookup:
            return lookup[candidate.lower()]
    return None


FILE_ID_COLUMNS = [
    "file_id", "fileid", "file", "filename", "file_name", "source_file",
    "recording", "recording_id", "subject_file", "actigraphy_file",
]


def _file_key_parts(value):
    if value is None:
        return set()
    text = str(value).strip().lower()
    if not text:
        return set()
    parts = {text}
    try:
        path = Path(text)
        parts.add(path.name)
        parts.add(path.stem)
    except Exception:
        pass
    return {part for part in parts if part}


def _matches_source_file(value, source_filename=None):
    if value is None or str(value).strip() == "":
        return True
    text = str(value).strip().lower()
    if text in {"all", "__all__", "global", "*"}:
        return True
    if not source_filename:
        return True
    return bool(_file_key_parts(value).intersection(_file_key_parts(source_filename)))


def _interval_applies_to_source(interval, source_filename=None):
    if not source_filename:
        return True
    file_id = (
        interval.get("fileId")
        or interval.get("file_id")
        or interval.get("fileName")
        or interval.get("filename")
        or interval.get("source_file")
    )
    return _matches_source_file(file_id, source_filename)


def _filter_table_for_source_file(df, source_filename=None):
    if df is None or not source_filename:
        return df, False
    file_col = _find_column(df, FILE_ID_COLUMNS)
    if not file_col:
        return df, False
    mask = df[file_col].apply(lambda value: _matches_source_file(value, source_filename))
    return df.loc[mask].copy(), True


def _normalize_start_stop_pair(start, stop):
    import pandas as pd

    start_ts = pd.to_datetime(start)
    stop_ts = pd.to_datetime(stop)
    if pd.isna(start_ts) or pd.isna(stop_ts):
        return None, None
    if stop_ts <= start_ts:
        # Supports midnight-crossing rows where users enter 23:00 -> 02:00
        # with the same calendar date, or diary exports with time-only values.
        stop_ts = stop_ts + pd.Timedelta(days=1)
    return start_ts, stop_ts


def _extract_sleep_windows_from_table(df, source_filename=None):
    import pandas as pd

    windows = []
    if df is None or len(df) == 0:
        return windows
    df, _had_file_filter = _filter_table_for_source_file(df, source_filename)
    if df is None or len(df) == 0:
        return windows

    state_col = _find_column(df, [
        "state", "type", "status", "event", "label", "period", "category", "sleep_state"
    ])
    start_col = _find_column(df, [
        "start", "start_time", "startTime", "onset", "begin", "from", "bedtime",
        "bed_time", "lights_off", "sleep_start", "Start_time"
    ])
    stop_col = _find_column(df, [
        "stop", "end", "end_time", "stopTime", "offset", "to", "wake_time",
        "wake", "rise_time", "get_up_time", "Stop_time"
    ])

    if not start_col or not stop_col:
        return windows

    night_like_terms = ("night", "sleep", "bed", "in_bed", "in bed", "main")
    excluded_terms = ("nap", "nowear", "no wear", "nonwear", "active")

    for _, row in df.iterrows():
        raw_state = str(row[state_col]).strip() if state_col else "NIGHT"
        state = raw_state.lower()
        if state_col:
            if any(term in state for term in excluded_terms):
                continue
            if not any(term in state for term in night_like_terms):
                continue
        try:
            start, stop = _normalize_start_stop_pair(row[start_col], row[stop_col])
            if start is None or stop is None or stop <= start:
                continue
            windows.append({
                "start": start.isoformat(),
                "stop": stop.isoformat(),
                "state": raw_state or "NIGHT",
                "source": "sleep_diary",
            })
        except Exception:
            continue
    return windows


def _read_sleep_diary_table(file_path: str, source_filename=None):
    # pyActigraphy sleep diaries often include a small preamble before the table;
    # try normal parsing first, then retry with skipped header rows.
    df = _read_support_table(file_path)
    if df is not None and _extract_sleep_windows_from_table(df, source_filename=source_filename):
        return df

    try:
        import pandas as pd
        for skiprows in range(1, 6):
            try:
                candidate = pd.read_csv(file_path, skiprows=skiprows)
                if _extract_sleep_windows_from_table(candidate, source_filename=source_filename):
                    return candidate
            except Exception:
                try:
                    candidate = pd.read_csv(file_path, sep=None, engine="python", skiprows=skiprows)
                    if _extract_sleep_windows_from_table(candidate, source_filename=source_filename):
                        return candidate
                except Exception:
                    pass
    except Exception:
        pass

    return df

def _apply_support_file_logic(raw, masking_paths=None, diary_paths=None, start_stop_paths=None, support_settings=None, source_filename=None):
    import pandas as pd

    support_settings = support_settings or {}
    start_stop_settings = support_settings.get("startStop", {}) or {}
    masking_settings = support_settings.get("masking", {}) or {}
    diary_settings = support_settings.get("sleepDiary", {}) or {}

    summary = {
        "masking_files_received": len(masking_paths or []),
        "sleep_diary_files_received": len(diary_paths or []),
        "start_stop_files_received": len(start_stop_paths or []),
        "manual_start_stop_intervals_received": len(start_stop_settings.get("manualIntervals", []) or []),
        "manual_mask_intervals_received": len(masking_settings.get("manualIntervals", []) or []),
        "manual_sleep_diary_windows_received": len(diary_settings.get("manualIntervals", []) or []),
        "mask_intervals_applied": 0,
        "sleep_diary_rows_loaded": 0,
        "sleep_windows_loaded": 0,
        "start_stop_applied": False,
        "source_file": source_filename,
        "notes": [],
    }

    def apply_interval(start, stop, source):
        if start is None or stop is None:
            return
        try:
            start_ts, stop_ts = _normalize_start_stop_pair(start, stop)
            if start_ts is None or stop_ts is None or stop_ts <= start_ts:
                summary["notes"].append(f"{source}: skipped invalid or empty interval.")
                return
            intervals = list(getattr(raw, "_ui_mask_intervals", None) or [])
            intervals.append({"start": start_ts.isoformat(), "stop": stop_ts.isoformat(), "source": source})
            raw._ui_mask_intervals = intervals
            summary["mask_intervals_applied"] += 1
        except Exception as exc:
            summary["notes"].append(f"{source}: could not apply interval ({exc}).")

    def apply_start_stop_window(start, stop, source="start/stop"):
        try:
            start, stop = _normalize_start_stop_pair(start, stop)
            if start is None or stop is None or stop <= start:
                summary["notes"].append(f"{source}: skipped invalid start/stop interval.")
                return
            raw._ui_analysis_start = start.isoformat()
            raw._ui_analysis_stop = stop.isoformat()
            summary["start_stop_applied"] = True
            summary["notes"].append(f"{source}: applied recording interval before masking and sleep scoring.")
        except Exception as exc:
            summary["notes"].append(f"{source}: data truncation failed ({exc}).")

    # 1) Apply start/stop first, because pyActigraphy's SST-log use case is to remove
    #    leading/trailing periods when the device was not yet worn or no longer worn.
    if start_stop_settings.get("apply", True):
        for interval in start_stop_settings.get("manualIntervals", []) or []:
            if not _interval_applies_to_source(interval, source_filename):
                continue
            apply_start_stop_window(interval.get("start"), interval.get("stop"), f"manual start/stop{f' for {source_filename}' if source_filename else ''}")

    for path in (start_stop_paths or []) if start_stop_settings.get("apply", True) else []:
        df = _read_support_table(path)
        start_col = _find_column(df, ["start", "start_time", "startTime", "onset", "begin", "Start_time"])
        stop_col = _find_column(df, ["stop", "end", "end_time", "stopTime", "offset", "Stop_time"])
        if df is not None and len(df) > 0 and start_col and stop_col:
            filtered_df, had_file_filter = _filter_table_for_source_file(df, source_filename)
            if filtered_df is None or len(filtered_df) == 0:
                if had_file_filter:
                    summary["notes"].append(f"Start/stop file had file IDs, but no rows matched {source_filename}.")
                continue
            for _, row in filtered_df.iterrows():
                apply_start_stop_window(row[start_col], row[stop_col], "start/stop file")
        else:
            summary["notes"].append("Start/stop file received, but start/stop columns were not recognized.")

    # 2) Apply masks after truncation.
    if masking_settings.get("apply", True):
        for interval in masking_settings.get("manualIntervals", []) or []:
            if not _interval_applies_to_source(interval, source_filename):
                continue
            apply_interval(interval.get("start"), interval.get("stop"), f"manual masking{f' for {source_filename}' if source_filename else ''}")

    for path in (masking_paths or []) if masking_settings.get("apply", True) else []:
        df = _read_support_table(path)
        start_col = _find_column(df, ["start", "start_time", "startTime", "onset", "begin", "Start_time"])
        stop_col = _find_column(df, ["stop", "end", "end_time", "stopTime", "offset", "Stop_time"])
        if df is not None and start_col and stop_col:
            filtered_df, had_file_filter = _filter_table_for_source_file(df, source_filename)
            if filtered_df is None or len(filtered_df) == 0:
                if had_file_filter:
                    summary["notes"].append(f"Masking file had file IDs, but no rows matched {source_filename}.")
                continue
            for _, row in filtered_df.iterrows():
                apply_interval(row[start_col], row[stop_col], "masking")
        else:
            summary["notes"].append("Masking file received, but start/stop columns were not recognized.")

    # 3) Load diary metadata last so downstream sleep summaries can use the cleaned/truncated signal.
    sleep_windows = []
    if diary_settings.get("apply", True):
        for interval in diary_settings.get("manualIntervals", []) or []:
            if not _interval_applies_to_source(interval, source_filename):
                continue
            try:
                start, stop = _normalize_start_stop_pair(interval.get("start"), interval.get("stop"))
                if start is None or stop is None or stop <= start:
                    continue
                state = str(interval.get("state") or "NIGHT")
                if state.lower() not in ("nap", "nowear", "no wear", "nonwear", "active"):
                    sleep_windows.append({
                        "start": start.isoformat(),
                        "stop": stop.isoformat(),
                        "state": state,
                        "source": "manual_sleep_diary",
                    })
                    summary["sleep_windows_loaded"] += 1
            except Exception as exc:
                summary["notes"].append(f"manual sleep diary: could not parse interval ({exc}).")

    for path in (diary_paths or []) if diary_settings.get("apply", True) else []:
        df = _read_sleep_diary_table(path, source_filename=source_filename)
        if df is not None:
            summary["sleep_diary_rows_loaded"] += int(len(df))
            windows = _extract_sleep_windows_from_table(df, source_filename=source_filename)
            sleep_windows.extend(windows)
            summary["sleep_windows_loaded"] += int(len(windows))
            if windows:
                summary["notes"].append(f"Loaded {len(windows)} sleep diary NIGHT/sleep window(s) for WASO and sleep efficiency.")
            else:
                summary["notes"].append("Sleep diary parsed, but no NIGHT/sleep windows were recognized.")
            if hasattr(raw, "read_sleep_diary"):
                try:
                    raw.read_sleep_diary(path)
                    summary["notes"].append("Sleep diary also loaded with raw.read_sleep_diary.")
                except Exception as exc:
                    summary["notes"].append(f"Sleep diary parsed but raw.read_sleep_diary failed ({exc}).")
            else:
                summary["notes"].append("Sleep diary parsed; this raw object does not expose read_sleep_diary.")
        else:
            summary["notes"].append("Sleep diary file received but could not be parsed.")

    # Store parsed windows on the raw object so analysis.py can calculate TST, WASO,
    # and sleep efficiency consistently across all scoring algorithms.
    try:
        raw._ui_sleep_windows = sleep_windows
    except Exception:
        pass

    if ("waso" in str(sleep_windows).lower() or "sleep_efficiency" in str(sleep_windows).lower()) and not sleep_windows:
        summary["notes"].append("WASO and sleep efficiency require a diary-defined in-bed/sleep window.")

    return summary



def _estimate_analysis_stage_total(metric_requests, family_requests, analysis_scope):
    """Estimate the stages visible in structured diagnostics.

    A full-file run with all ten rest/activity metrics and all four sleep
    metrics has 26 stages: ten request/pipeline stages, ten metric stages,
    two sleep setup stages, and four sleep-metric stages. Selected-interval
    runs can add more metric stages; DiagnosticSession grows the total if
    additional stages are encountered.
    """
    rest_ids = {"ra", "is", "iv", "ism", "ivm", "isp", "ivp", "rap", "kra", "kar"}
    sleep_ids = {"sri", "tst", "waso", "sleep_efficiency"}
    selected = [item.get("id") for item in (metric_requests or []) if item.get("id")]
    if analysis_scope == "family" and not selected:
        family_map = {
            "amplitude": ["ra", "rap"],
            "rhythm": ["is", "iv", "ism", "ivm", "isp", "ivp"],
            "sleep": ["sri", "tst", "waso", "sleep_efficiency"],
            "fragmentation": ["kra", "kar"],
        }
        for family in family_requests or []:
            selected.extend(family_map.get(family.get("id"), []))
    selected = list(dict.fromkeys(selected))
    rest_count = sum(metric_id in rest_ids for metric_id in selected)
    sleep_count = sum(metric_id in sleep_ids for metric_id in selected)
    base_pipeline_stages = 10
    sleep_setup_stages = 2 if sleep_count else 0
    return base_pipeline_stages + rest_count + sleep_setup_stages + sleep_count

@app.post("/api/analyze/basic")
def analyze_basic(
    file: UploadFile = File(...),
    activityChannel: str = Form("VM"),
    activityMapping: str = Form("auto"),
    activityTransform: str = Form("none"),
    lightTransform: str = Form("none"),
    analysisMode: str = Form("standard"),
    analysisConfig: str = Form("{}"),
    csvMapping: str = Form("{}"),
    csvSeparator: str = Form(","),
    maskingFiles: Optional[List[UploadFile]] = File(None),
    sleepDiaryFiles: Optional[List[UploadFile]] = File(None),
    startStopFiles: Optional[List[UploadFile]] = File(None),
    sourceFileName: Optional[str] = Form(None),
    requestId: Optional[str] = Form(None),
):
    source_filename = sourceFileName or file.filename
    session = DiagnosticSession(
        "/api/analyze/basic",
        source_file_name=source_filename,
        request_id=requestId,
        expected_stage_total=10,
    ).activate()
    temp_paths = []
    status_code = 200
    response_content = {}
    final_status = "completed"
    caught_exception = None

    try:
        with session.stage("request.parse_analysis_config", category="request"):
            analysis_config = json.loads(analysisConfig or "{}")
            requested_mapping = normalize_activity_mapping(activityMapping)
            metric_requests = analysis_config.get("metrics", [])
            family_requests = analysis_config.get("families", [])
            analysis_scope = analysis_config.get("analysisScope", "metric")
            algorithm_request = analysis_config.get("algorithm")
            sleep_window_settings = analysis_config.get("sleepWindowSettings", {})
            session.set_expected_stage_total(
                _estimate_analysis_stage_total(metric_requests, family_requests, analysis_scope)
            )
            analysis_window_settings = analysis_config.get("analysisWindowSettings", {}) or {}
            analysis_window_settings = {**analysis_window_settings, "sourceFileName": source_filename}
            parsed_csv_mapping = _clean_csv_mapping(csvMapping)
            update_current_stage(
                analysis_mode=analysisMode,
                analysis_scope=analysis_scope,
                requested_metrics=[item.get("id") for item in metric_requests if item.get("id")],
                requested_families=[item.get("id") for item in family_requests if item.get("id")],
                algorithm=(algorithm_request or {}).get("id"),
                analysis_window_mode=analysis_window_settings.get("mode", "full"),
                activity_mapping_requested=requested_mapping,
                support_file_counts={
                    "masking": len(maskingFiles or []),
                    "sleep_diary": len(sleepDiaryFiles or []),
                    "start_stop": len(startStopFiles or []),
                },
            )

        with session.stage("upload.primary_file", category="upload"):
            tmp_path = _write_upload_to_temp(file)
            temp_paths.append(tmp_path)
            session.input_file = uploaded_file_summary(
                tmp_path,
                original_name=source_filename,
                content_type=file.content_type,
            )
            update_current_stage(**session.input_file)

        with session.stage("input.detect_reader", category="reader"):
            reader_type = infer_reader_type(tmp_path)
            update_current_stage(detected_input_type=reader_type)

        with session.stage(
            "input.load_recording",
            category="reader",
            details={"detected_input_type": reader_type},
        ):
            raw, reader_type = _load_native_supported_file(
                tmp_path,
                activity_mapping=requested_mapping,
                csv_mapping=parsed_csv_mapping,
                csv_separator=csvSeparator,
            )
            mapping_details = raw_mapping_metadata(raw)
            update_current_stage(
                raw_class=type(raw).__name__,
                raw_module=type(raw).__module__,
                activity_mapping=mapping_details,
            )

        with session.stage("input.inspect_recording", category="data_validation"):
            session.recording = raw_recording_summary(raw)
            update_current_stage(**session.recording)
            data_summary = session.recording.get("data", {})
            if not data_summary.get("available"):
                raise ValueError("The file loaded, but the reader did not expose an activity data series.")
            activity_summary = data_summary.get("activity", {})
            if activity_summary.get("valid_rows", 0) < 2:
                raise ValueError("The file loaded, but fewer than two valid activity rows were available.")
            if activity_summary.get("zero_fraction") == 1:
                mark_current_stage("warning", outcome="activity_series_is_entirely_zero")

        masking_paths = []
        diary_paths = []
        start_stop_paths = []
        with session.stage("upload.support_files", category="upload"):
            support_upload_summaries = {"masking": [], "sleep_diary": [], "start_stop": []}
            for item in maskingFiles or []:
                path = _write_upload_to_temp(item)
                temp_paths.append(path)
                masking_paths.append(path)
                support_upload_summaries["masking"].append(uploaded_file_summary(path, item.filename, item.content_type))
            for item in sleepDiaryFiles or []:
                path = _write_upload_to_temp(item)
                temp_paths.append(path)
                diary_paths.append(path)
                support_upload_summaries["sleep_diary"].append(uploaded_file_summary(path, item.filename, item.content_type))
            for item in startStopFiles or []:
                path = _write_upload_to_temp(item)
                temp_paths.append(path)
                start_stop_paths.append(path)
                support_upload_summaries["start_stop"].append(uploaded_file_summary(path, item.filename, item.content_type))
            update_current_stage(files=support_upload_summaries)

        with session.stage("preprocessing.apply_support_files", category="preprocessing"):
            support_file_summary = _apply_support_file_logic(
                raw,
                masking_paths=masking_paths,
                diary_paths=diary_paths,
                start_stop_paths=start_stop_paths,
                support_settings=analysis_config.get("supportFileSettings", {}),
                source_filename=source_filename,
            )
            update_current_stage(summary=support_file_summary)
            session.recording["after_support_files"] = raw_recording_summary(raw).get("data", {})

        with session.stage("preprocessing.missingness_nonwear_valid_days", category="preprocessing"):
            raw, data_quality = apply_data_quality_control(
                raw,
                support_settings=analysis_config.get("supportFileSettings", {}),
            )
            update_current_stage(
                settings=data_quality.get("settings"),
                calendar_days=data_quality.get("calendar_days"),
                valid_days=data_quality.get("valid_days"),
                longest_consecutive_valid_days=data_quality.get("longest_consecutive_valid_days"),
                invalid_days=data_quality.get("invalid_days"),
                completely_missing_days=data_quality.get("completely_missing_days"),
                detected_nonwear_hours=data_quality.get("detected_nonwear_hours"),
                manual_mask_hours=data_quality.get("manual_mask_hours"),
                recording_gap_hours=data_quality.get("recording_gap_hours"),
            )
            if data_quality.get("warnings"):
                mark_current_stage("warning", warnings=data_quality.get("warnings"))
            session.recording["after_data_quality"] = raw_recording_summary(raw).get("data", {})

        with session.stage("analysis.execute", category="analysis"):
            results = run_basic_pyactigraphy_analysis(
                raw=raw,
                metric_requests=metric_requests,
                family_requests=family_requests,
                analysis_scope=analysis_scope,
                algorithm_request=algorithm_request,
                sleep_window_settings=sleep_window_settings,
                analysis_window_settings=analysis_window_settings,
            )
            update_current_stage(result_keys=list(results.keys()), result_count=len(results))

        with session.stage("analysis.quality_control", category="quality_control"):
            try:
                warnings = quick_qc(results)
            except Exception as qc_exc:
                # Quality-control checks are advisory. Preserve the metric results
                # even if a future QC rule encounters an unexpected return type.
                record_suppressed_exception(
                    "quick_qc",
                    qc_exc,
                    note="QC is non-fatal; analysis metric results were preserved.",
                )
                warnings = [
                    "Automated quality-control checks could not be completed. "
                    "The calculated metric results were preserved; see diagnostics for the QC exception."
                ]

            warnings = list(data_quality.get("warnings") or []) + list(warnings or [])

            if requested_mapping != "original" and (algorithm_request or {}).get("id"):
                warnings.append(
                    f"{requested_mapping.upper()} was used as the activity mapping. "
                    "Sleep-algorithm thresholds validated for device counts may not transfer directly to mg units."
                )

            if warnings:
                mark_current_stage("warning", warning_count=len(warnings), warnings=warnings)
            else:
                update_current_stage(warning_count=0, warnings=[])

        failed_or_warning_stages = [
            stage for stage in session.stages
            if stage.get("status") in {"failed", "warning"}
            and stage.get("name") not in {"analysis.execute"}
        ]
        if failed_or_warning_stages:
            final_status = "completed_with_warnings"

        response_content = {
            "results": results,
            "qcWarnings": warnings,
            "supportFileSummary": support_file_summary,
            "dataQuality": data_quality,
            "detected_input_type": reader_type,
            "native_reader_used": reader_type != "tabular_mapped",
            "activity_mapping": mapping_details,
        }

    except ValueError as exc:
        caught_exception = exc
        final_status = "failed"
        status_code = 400
        response_content = {"detail": str(exc)}
    except Exception as exc:
        caught_exception = exc
        final_status = "failed"
        status_code = 500
        response_content = {"detail": "Server error: {}".format(str(exc))}
    finally:
        try:
            with session.stage("request.cleanup_temp_files", category="cleanup"):
                cleanup_summary = _cleanup_temp_paths(temp_paths)
                update_current_stage(**cleanup_summary)
                if cleanup_summary.get("errors"):
                    mark_current_stage("warning")
        except Exception:
            pass

        session.finish(final_status, caught_exception)
        diagnostics_payload = session.payload()
        response_content["diagnostics"] = diagnostics_payload
        _persist_diagnostics(diagnostics_payload)
        session.deactivate()

    return _safe_json_response(status_code=status_code, content=response_content)


def _background_preview_worker(primary_spec: dict, options: dict) -> dict:
    uploads, opened = _uploads_from_job_specs([primary_spec])
    try:
        response = preview_basic(
            file=uploads[0],
            activityChannel=options.get("activityChannel", "VM"),
            activityMapping=options.get("activityMapping", "auto"),
            resampleFreq=options.get("resampleFreq", "1min"),
            csvMapping=options.get("csvMapping", "{}"),
            csvSeparator=options.get("csvSeparator", ","),
        )
        return _response_outcome(response)
    finally:
        for handle in opened:
            try:
                handle.close()
            except Exception:
                pass


def _background_light_worker(primary_spec: dict, operation: str, options: dict) -> dict:
    """Run a light read operation after the upload request has returned."""
    uploads, opened = _uploads_from_job_specs([primary_spec])
    try:
        upload = uploads[0]
        if operation == "preview":
            response = preview_light(
                file=upload,
                resampleFreq=options.get("resampleFreq", "1min"),
                rgbResampleFreq=options.get("rgbResampleFreq", "5min"),
                csvMapping=options.get("csvMapping", "{}"),
                csvSeparator=options.get("csvSeparator", ","),
                maskingFiles=None,
                sleepDiaryFiles=None,
                startStopFiles=None,
            )
        elif operation == "rgb_preview":
            response = preview_light_rgb(
                file=upload,
                resampleFreq=options.get("resampleFreq", "5min"),
            )
        elif operation == "channels":
            response = light_channels(file=upload)
        elif operation == "analyze":
            response = analyze_light_batch(
                file=upload,
                metricIds=options.get("metricIds", "[]"),
                channel=options.get("channel") or None,
                thresholdLux=options.get("thresholdLux") or None,
                startTime=options.get("startTime") or None,
                stopTime=options.get("stopTime") or None,
                bins=options.get("bins", "24h"),
                agg=options.get("agg", "mean"),
                aggFuncs=options.get("aggFuncs", ""),
                outputFormat=options.get("outputFormat", "minute"),
                lmxLength=options.get("lmxLength", "5h"),
                lowest=options.get("lowest", "true"),
                binarize=options.get("binarize", "false"),
                csvMapping=options.get("csvMapping", "{}"),
                csvSeparator=options.get("csvSeparator", ","),
                requestId=options.get("requestId"),
            )
        else:
            raise ValueError(f"Unsupported background light operation: {operation}")
        return _response_outcome(response)
    finally:
        for handle in opened:
            try:
                handle.close()
            except Exception:
                pass


def _background_analysis_worker(primary_spec: dict, support_specs: dict, options: dict) -> dict:
    primary_uploads, primary_opened = _uploads_from_job_specs([primary_spec])
    masking_uploads, masking_opened = _uploads_from_job_specs(support_specs.get("masking"))
    diary_uploads, diary_opened = _uploads_from_job_specs(support_specs.get("sleep_diary"))
    start_stop_uploads, start_stop_opened = _uploads_from_job_specs(support_specs.get("start_stop"))
    opened = primary_opened + masking_opened + diary_opened + start_stop_opened
    try:
        response = analyze_basic(
            file=primary_uploads[0],
            activityChannel=options.get("activityChannel", "VM"),
            activityMapping=options.get("activityMapping", "auto"),
            activityTransform=options.get("activityTransform", "none"),
            lightTransform=options.get("lightTransform", "none"),
            analysisMode=options.get("analysisMode", "standard"),
            analysisConfig=options.get("analysisConfig", "{}"),
            csvMapping=options.get("csvMapping", "{}"),
            csvSeparator=options.get("csvSeparator", ","),
            maskingFiles=masking_uploads or None,
            sleepDiaryFiles=diary_uploads or None,
            startStopFiles=start_stop_uploads or None,
            sourceFileName=options.get("sourceFileName"),
            requestId=options.get("requestId"),
        )
        return _response_outcome(response)
    finally:
        for handle in opened:
            try:
                handle.close()
            except Exception:
                pass


def _start_background_light_job(
    *,
    file: UploadFile,
    operation: str,
    options: dict,
    requested_job_id: Optional[str],
):
    created_job_id = None
    try:
        # Capability is content-based. GT3X files enter the queue and use the
        # light-only streaming reader; files without lux records finish as a
        # successful, explicit skip rather than a crash or format rejection.
        _validate_light_upload_format(file)
        created_job_id, directory = create_job_record(
            f"light_{operation}",
            requested_job_id=requested_job_id,
            request_id=requested_job_id,
            source_file_name=file.filename,
        )
        primary_spec = _write_upload_to_job(file, directory, "light")
        submit_job(
            created_job_id,
            lambda: _background_light_worker(primary_spec, operation, options),
        )
        return JSONResponse(
            status_code=202,
            content={
                "ok": True,
                "job_id": created_job_id,
                "request_id": created_job_id,
                "status": "queued",
                "status_url": f"/api/jobs/{created_job_id}",
                "operation": operation,
                "runtime": job_runtime_info(),
            },
        )
    except ValueError as exc:
        return JSONResponse(
            status_code=400,
            content={
                "ok": False,
                "code": "unsupported_light_source",
                "detail": str(exc),
            },
        )
    except Exception as exc:
        if created_job_id:
            try:
                update_job(
                    created_job_id,
                    status="failed",
                    message=str(exc),
                    finished_at=datetime.now(timezone.utc).isoformat(),
                )
            except Exception:
                pass
        return JSONResponse(
            status_code=500,
            content={"ok": False, "detail": f"Could not start light {operation} job: {exc}"},
        )


@app.get("/api/jobs/{job_id}")
def background_job_status(job_id: str):
    record = get_job(job_id)
    if record is None:
        return JSONResponse(
            status_code=404,
            content={
                "ok": False,
                "code": "background_job_not_found",
                "detail": (
                    "Background job state is not visible on this backend instance. "
                    "This is retryable briefly; persistent failures usually mean polling "
                    "reached another replica/revision or the original replica restarted."
                ),
                "retryable": True,
                "runtime": job_runtime_info(),
            },
        )

    payload = {"ok": True, **record, "runtime": job_runtime_info()}
    request_id = record.get("request_id")
    progress_payload = get_progress(request_id) if request_id else None
    if progress_payload is not None:
        payload["progress"] = progress_payload

    if record.get("result_available"):
        stored_result = get_job_result(job_id) or {}
        payload["result_http_status"] = int(stored_result.get("http_status", 500))
        payload["result"] = stored_result.get("content", {})
    return _safe_json_response(status_code=200, content=payload)


@app.post("/api/jobs/preview/basic")
def start_background_preview_basic(
    file: UploadFile = File(...),
    activityChannel: str = Form("VM"),
    activityMapping: str = Form("auto"),
    resampleFreq: str = Form("1min"),
    csvMapping: str = Form("{}"),
    csvSeparator: str = Form(","),
    jobId: Optional[str] = Form(None),
):
    created_job_id = None
    try:
        created_job_id, directory = create_job_record(
            "preview_basic",
            requested_job_id=jobId,
            request_id=jobId,
            source_file_name=file.filename,
        )
        primary_spec = _write_upload_to_job(file, directory, "primary")
        options = {
            "activityChannel": activityChannel,
            "activityMapping": activityMapping,
            "resampleFreq": resampleFreq,
            "csvMapping": csvMapping,
            "csvSeparator": csvSeparator,
        }
        submit_job(
            created_job_id,
            lambda: _background_preview_worker(primary_spec, options),
        )
        return JSONResponse(
            status_code=202,
            content={
                "ok": True,
                "job_id": created_job_id,
                "request_id": created_job_id,
                "status": "queued",
                "status_url": f"/api/jobs/{created_job_id}",
                "runtime": job_runtime_info(),
            },
        )
    except Exception as exc:
        if created_job_id:
            try:
                update_job(created_job_id, status="failed", message=str(exc), finished_at=datetime.now(timezone.utc).isoformat())
            except Exception:
                pass
        return JSONResponse(status_code=500, content={"ok": False, "detail": f"Could not start preview job: {exc}"})


@app.post("/api/jobs/light/preview")
def start_background_light_preview(
    file: UploadFile = File(...),
    resampleFreq: str = Form("1min"),
    rgbResampleFreq: str = Form("5min"),
    csvMapping: str = Form("{}"),
    csvSeparator: str = Form(","),
    jobId: Optional[str] = Form(None),
):
    return _start_background_light_job(
        file=file,
        operation="preview",
        options={
            "resampleFreq": resampleFreq,
            "rgbResampleFreq": rgbResampleFreq,
            "csvMapping": csvMapping,
            "csvSeparator": csvSeparator,
        },
        requested_job_id=jobId,
    )


@app.post("/api/jobs/light/rgb-preview")
def start_background_light_rgb_preview(
    file: UploadFile = File(...),
    resampleFreq: str = Form("5min"),
    jobId: Optional[str] = Form(None),
):
    return _start_background_light_job(
        file=file,
        operation="rgb_preview",
        options={"resampleFreq": resampleFreq},
        requested_job_id=jobId,
    )


@app.post("/api/jobs/light/channels")
def start_background_light_channels(
    file: UploadFile = File(...),
    jobId: Optional[str] = Form(None),
):
    return _start_background_light_job(
        file=file,
        operation="channels",
        options={},
        requested_job_id=jobId,
    )


@app.post("/api/jobs/light/analyze")
def start_background_light_analysis(
    file: UploadFile = File(...),
    metricIds: str = Form("[]"),
    channel: Optional[str] = Form(None),
    thresholdLux: Optional[str] = Form(None),
    startTime: Optional[str] = Form(None),
    stopTime: Optional[str] = Form(None),
    bins: str = Form("24h"),
    agg: str = Form("mean"),
    aggFuncs: str = Form(""),
    outputFormat: str = Form("minute"),
    lmxLength: str = Form("5h"),
    lowest: str = Form("true"),
    binarize: str = Form("false"),
    csvMapping: str = Form("{}"),
    csvSeparator: str = Form(","),
    requestId: Optional[str] = Form(None),
    jobId: Optional[str] = Form(None),
):
    resolved_job_id = jobId or requestId
    return _start_background_light_job(
        file=file,
        operation="analyze",
        options={
            "metricIds": metricIds,
            "channel": channel or "",
            "thresholdLux": thresholdLux or "",
            "startTime": startTime or "",
            "stopTime": stopTime or "",
            "bins": bins,
            "agg": agg,
            "aggFuncs": aggFuncs,
            "outputFormat": outputFormat,
            "lmxLength": lmxLength,
            "lowest": lowest,
            "binarize": binarize,
            "csvMapping": csvMapping,
            "csvSeparator": csvSeparator,
            "requestId": requestId or resolved_job_id,
        },
        requested_job_id=resolved_job_id,
    )


@app.post("/api/jobs/analyze/basic")
def start_background_analyze_basic(
    file: UploadFile = File(...),
    activityChannel: str = Form("VM"),
    activityMapping: str = Form("auto"),
    activityTransform: str = Form("none"),
    lightTransform: str = Form("none"),
    analysisMode: str = Form("standard"),
    analysisConfig: str = Form("{}"),
    csvMapping: str = Form("{}"),
    csvSeparator: str = Form(","),
    maskingFiles: Optional[List[UploadFile]] = File(None),
    sleepDiaryFiles: Optional[List[UploadFile]] = File(None),
    startStopFiles: Optional[List[UploadFile]] = File(None),
    sourceFileName: Optional[str] = Form(None),
    requestId: Optional[str] = Form(None),
    jobId: Optional[str] = Form(None),
):
    created_job_id = None
    source_filename = sourceFileName or file.filename
    try:
        created_job_id, directory = create_job_record(
            "analyze_basic",
            requested_job_id=jobId or requestId,
            request_id=requestId or jobId,
            source_file_name=source_filename,
        )
        effective_request_id = requestId or created_job_id
        primary_spec = _write_upload_to_job(file, directory, "primary")
        support_specs = {"masking": [], "sleep_diary": [], "start_stop": []}
        for index, upload in enumerate(maskingFiles or []):
            support_specs["masking"].append(_write_upload_to_job(upload, directory, f"masking-{index}"))
        for index, upload in enumerate(sleepDiaryFiles or []):
            support_specs["sleep_diary"].append(_write_upload_to_job(upload, directory, f"diary-{index}"))
        for index, upload in enumerate(startStopFiles or []):
            support_specs["start_stop"].append(_write_upload_to_job(upload, directory, f"start-stop-{index}"))
        options = {
            "activityChannel": activityChannel,
            "activityMapping": activityMapping,
            "activityTransform": activityTransform,
            "lightTransform": lightTransform,
            "analysisMode": analysisMode,
            "analysisConfig": analysisConfig,
            "csvMapping": csvMapping,
            "csvSeparator": csvSeparator,
            "sourceFileName": source_filename,
            "requestId": effective_request_id,
        }
        submit_job(
            created_job_id,
            lambda: _background_analysis_worker(primary_spec, support_specs, options),
        )
        return JSONResponse(
            status_code=202,
            content={
                "ok": True,
                "job_id": created_job_id,
                "request_id": effective_request_id,
                "status": "queued",
                "status_url": f"/api/jobs/{created_job_id}",
                "runtime": job_runtime_info(),
            },
        )
    except Exception as exc:
        if created_job_id:
            try:
                update_job(created_job_id, status="failed", message=str(exc), finished_at=datetime.now(timezone.utc).isoformat())
            except Exception:
                pass
        return JSONResponse(status_code=500, content={"ok": False, "detail": f"Could not start analysis job: {exc}"})
