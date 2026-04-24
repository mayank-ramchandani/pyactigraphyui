from typing import Optional
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import json
import tempfile
from pathlib import Path

from .analysis import (
    run_basic_pyactigraphy_analysis,
    build_native_preview,
    build_light_preview,
    run_basic_pylight_analysis,
    get_basic_light_channels,
)
from .qc import quick_qc
from .io_helpers import (
    load_native_file,
    infer_reader_type,
)

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "https://actigraphy-ui.vercel.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _write_upload_to_temp(upload: UploadFile):
    suffix = Path(upload.filename).suffix.lower()
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(upload.file.read())
        return tmp.name


def _json_or_empty(value):
    try:
        return json.loads(value or "{}")
    except Exception:
        return {}


def _load_native_supported_file(file_path: str):
    reader_type = infer_reader_type(file_path)

    if reader_type == "tabular":
        raise ValueError(
            "This file is currently being detected as a generic tabular file, not a native "
            "pyActigraphy-supported format. For the simple tutorial-like path, the file must be "
            "recognized by a native reader first."
        )

    raw = load_native_file(file_path, reader_type)
    return raw, reader_type


@app.post("/api/preview/basic")
async def preview_basic(
    file: UploadFile = File(...),
    activityChannel: str = Form("VM"),
    resampleFreq: str = Form("1min"),
    csvMapping: str = Form("{}"),   # accepted for frontend compatibility, ignored here
    csvSeparator: str = Form(","),  # accepted for frontend compatibility, ignored here
):
    try:
        _json_or_empty(csvMapping)

        tmp_path = _write_upload_to_temp(file)
        raw, reader_type = _load_native_supported_file(tmp_path)

        preview = build_native_preview(
            raw=raw,
            activity_channel=activityChannel,
            resample_freq=resampleFreq,
        )

        return JSONResponse(
            content={
                **preview,
                "detected_input_type": reader_type,
                "native_reader_used": True,
            }
        )

    except ValueError as e:
        return JSONResponse(status_code=400, content={"detail": str(e)})
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"detail": "Server error: {}".format(str(e))}
        )


@app.post("/api/light/preview")
async def preview_light(
    file: UploadFile = File(...),
    resampleFreq: str = Form("1min"),
    csvMapping: str = Form("{}"),   # accepted for frontend compatibility, ignored here
    csvSeparator: str = Form(","),  # accepted for frontend compatibility, ignored here
):
    try:
        _json_or_empty(csvMapping)

        tmp_path = _write_upload_to_temp(file)
        raw, reader_type = _load_native_supported_file(tmp_path)

        preview = build_light_preview(raw=raw, resample_freq=resampleFreq)

        if not preview.get("light_preview_available"):
            return JSONResponse(
                status_code=400,
                content={
                    "detail": "The native reader loaded the file, but no embedded light channel was found.",
                    "detected_input_type": reader_type,
                    "native_reader_used": True,
                },
            )

        return JSONResponse(
            content={
                **preview,
                "detected_input_type": reader_type,
                "native_reader_used": True,
            }
        )

    except ValueError as e:
        return JSONResponse(status_code=400, content={"detail": str(e)})
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"detail": "Server error: {}".format(str(e))}
        )

@app.post("/api/light/channels")
async def light_channels(
    file: UploadFile = File(...),
):
    try:
        tmp_path = _write_upload_to_temp(file)
        raw, reader_type = _load_native_supported_file(tmp_path)

        payload = get_basic_light_channels(raw)

        return JSONResponse(
            content={
                **payload,
                "detected_input_type": reader_type,
                "native_reader_used": True,
            }
        )

    except ValueError as e:
        return JSONResponse(status_code=400, content={"detail": str(e)})
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"detail": "Server error: {}".format(str(e))}
        )


@app.post("/api/light/analyze")
async def analyze_light(
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
):
    try:
        tmp_path = _write_upload_to_temp(file)
        raw, reader_type = _load_native_supported_file(tmp_path)

        agg_funcs = [x.strip() for x in aggFuncs.split(",") if x.strip()] if aggFuncs else None

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
        )

        return JSONResponse(
            content={
                **payload,
                "detected_input_type": reader_type,
                "native_reader_used": True,
            }
        )

    except ValueError as e:
        return JSONResponse(status_code=400, content={"detail": str(e)})
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"detail": "Server error: {}".format(str(e))}
        )


@app.post("/api/analyze/basic")
async def analyze_basic(
    file: UploadFile = File(...),
    activityChannel: str = Form("VM"),
    activityTransform: str = Form("none"),
    lightTransform: str = Form("none"),
    analysisMode: str = Form("standard"),
    analysisConfig: str = Form("{}"),
    csvMapping: str = Form("{}"),   # accepted for frontend compatibility, ignored here
    csvSeparator: str = Form(","),  # accepted for frontend compatibility, ignored here
):
    try:
        analysis_config = json.loads(analysisConfig or "{}")
        metric_requests = analysis_config.get("metrics", [])
        family_requests = analysis_config.get("families", [])
        analysis_scope = analysis_config.get("analysisScope", "metric")
        algorithm_request = analysis_config.get("algorithm")
        _json_or_empty(csvMapping)

        tmp_path = _write_upload_to_temp(file)
        raw, reader_type = _load_native_supported_file(tmp_path)

        results = run_basic_pyactigraphy_analysis(
            raw=raw,
            metric_requests=metric_requests,
            family_requests=family_requests,
            analysis_scope=analysis_scope,
            algorithm_request=algorithm_request,
        )

        warnings = quick_qc(results)

        return JSONResponse(
            content={
                "results": results,
                "qcWarnings": warnings,
                "detected_input_type": reader_type,
                "native_reader_used": True,
            }
        )

    except ValueError as e:
        return JSONResponse(status_code=400, content={"detail": str(e)})
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"detail": "Server error: {}".format(str(e))}
        )