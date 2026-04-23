from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import json
import tempfile
from pathlib import Path

from .analysis import (
    run_basic_pyactigraphy_analysis,
    run_basic_csv_analysis,
    build_basic_preview,
    build_native_preview,
)
from .qc import quick_qc
from .io_helpers import load_native_file, infer_reader_type, validate_csv_file

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


@app.post("/api/analyze/basic")
async def analyze_basic(
    file: UploadFile = File(...),
    activityChannel: str = Form("VM"),
    activityTransform: str = Form("none"),
    lightTransform: str = Form("none"),
    analysisMode: str = Form("standard"),
    analysisConfig: str = Form("{}"),
):
    try:
        analysis_config = json.loads(analysisConfig or "{}")
        metric_requests = analysis_config.get("metrics", [])
        algorithm_request = analysis_config.get("algorithm")

        suffix = Path(file.filename).suffix.lower().replace(".", "")

        with tempfile.NamedTemporaryFile(delete=False, suffix=f".{suffix}") as tmp:
            content = await file.read()
            tmp.write(content)
            tmp_path = tmp.name

        reader_type = infer_reader_type(tmp_path)

        if reader_type == "csv":
            df = validate_csv_file(tmp_path)
            selected_metric_ids = [item.get("id") for item in metric_requests if item.get("id")]
            results = run_basic_csv_analysis(
                df=df,
                selected_metrics=selected_metric_ids,
                activity_channel=activityChannel,
                resample_freq="1min",
                analysis_mode=analysisMode,
                advanced_metric_params={},
            )
        else:
            raw = load_native_file(tmp_path, reader_type)
            results = run_basic_pyactigraphy_analysis(
                raw=raw,
                metric_requests=metric_requests,
                algorithm_request=algorithm_request,
            )

        warnings = quick_qc(results)
        return JSONResponse(content={"results": results, "qcWarnings": warnings})

    except ValueError as e:
        return JSONResponse(status_code=400, content={"detail": str(e)})
    except Exception as e:
        return JSONResponse(status_code=500, content={"detail": f"Server error: {str(e)}"})


@app.post("/api/preview/basic")
async def preview_basic(
    file: UploadFile = File(...),
    previewDayMode: str = Form("all"),
    activityChannel: str = Form("VM"),
    resampleFreq: str = Form("1min"),
):
    try:
        suffix = Path(file.filename).suffix.lower().replace(".", "")

        with tempfile.NamedTemporaryFile(delete=False, suffix=f".{suffix}") as tmp:
            content = await file.read()
            tmp.write(content)
            tmp_path = tmp.name

        reader_type = infer_reader_type(tmp_path)

        if reader_type == "csv":
            df = validate_csv_file(tmp_path)
            preview = build_basic_preview(
                df=df,
                preview_day_mode=previewDayMode,
                activity_channel=activityChannel,
                resample_freq=resampleFreq,
            )
        else:
            raw = load_native_file(tmp_path, reader_type)
            preview = build_native_preview(
                raw=raw,
                activity_channel=activityChannel,
                resample_freq=resampleFreq,
            )

        return JSONResponse(content=preview)

    except ValueError as e:
        return JSONResponse(status_code=400, content={"detail": str(e)})
    except Exception as e:
        return JSONResponse(status_code=500, content={"detail": f"Server error: {str(e)}"})