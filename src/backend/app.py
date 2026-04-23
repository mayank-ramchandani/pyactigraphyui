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
)
from .qc import quick_qc
from .io_helpers import (
    load_native_file,
    infer_reader_type,
    load_custom_csv,
    build_baseraw_from_dataframe,
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
        content = upload.file.read()
        tmp.write(content)
        return tmp.name


@app.post("/api/analyze/basic")
async def analyze_basic(
    file: UploadFile = File(...),
    activityChannel: str = Form("VM"),
    activityTransform: str = Form("none"),
    lightTransform: str = Form("none"),
    analysisMode: str = Form("standard"),
    analysisConfig: str = Form("{}"),
    csvMapping: str = Form("{}"),
    csvSeparator: str = Form(","),
):
    try:
        analysis_config = json.loads(analysisConfig or "{}")
        metric_requests = analysis_config.get("metrics", [])
        family_requests = analysis_config.get("families", [])
        analysis_scope = analysis_config.get("analysisScope", "metric")
        algorithm_request = analysis_config.get("algorithm")
        csv_mapping = json.loads(csvMapping or "{}")

        tmp_path = _write_upload_to_temp(file)
        reader_type = infer_reader_type(tmp_path)

        if reader_type == "csv":
            if not csv_mapping.get("timestamp_col") or not csv_mapping.get("activity_col"):
                raise ValueError("CSV files require timestamp and activity column mapping before analysis.")

            mapped_df = load_custom_csv(
                tmp_path,
                timestamp_col=csv_mapping.get("timestamp_col"),
                activity_col=csv_mapping.get("activity_col"),
                light_col=csv_mapping.get("light_col") or None,
                temperature_col=csv_mapping.get("temperature_col") or None,
                nonwear_col=csv_mapping.get("nonwear_col") or None,
                sep=csvSeparator,
            )
            raw = build_baseraw_from_dataframe(mapped_df, name=file.filename)
        else:
            raw = load_native_file(tmp_path, reader_type)

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
            }
        )

    except ValueError as e:
        return JSONResponse(status_code=400, content={"detail": str(e)})
    except Exception as e:
        return JSONResponse(status_code=500, content={"detail": f"Server error: {str(e)}"})


@app.post("/api/preview/basic")
async def preview_basic(
    file: UploadFile = File(...),
    lightFile: Optional[UploadFile] = File(None),
    activityChannel: str = Form("VM"),
    resampleFreq: str = Form("1min"),
    csvMapping: str = Form("{}"),
    csvSeparator: str = Form(","),
):
    try:
        csv_mapping = json.loads(csvMapping or "{}")

        tmp_path = _write_upload_to_temp(file)
        reader_type = infer_reader_type(tmp_path)

        if reader_type == "csv":
            if not csv_mapping.get("timestamp_col") or not csv_mapping.get("activity_col"):
                raise ValueError("CSV files require timestamp and activity column mapping before preview.")

            mapped_df = load_custom_csv(
                tmp_path,
                timestamp_col=csv_mapping.get("timestamp_col"),
                activity_col=csv_mapping.get("activity_col"),
                light_col=csv_mapping.get("light_col") or None,
                temperature_col=csv_mapping.get("temperature_col") or None,
                nonwear_col=csv_mapping.get("nonwear_col") or None,
                sep=csvSeparator,
            )
            raw = build_baseraw_from_dataframe(mapped_df, name=file.filename)
            preview = build_native_preview(
                raw=raw,
                activity_channel=activityChannel,
                resample_freq=resampleFreq,
            )
            light_preview = build_light_preview(raw=raw, resample_freq=resampleFreq)
        else:
            raw = load_native_file(tmp_path, reader_type)
            preview = build_native_preview(
                raw=raw,
                activity_channel=activityChannel,
                resample_freq=resampleFreq,
            )
            light_preview = build_light_preview(raw=raw, resample_freq=resampleFreq)

        if (not light_preview.get("light_preview_available")) and lightFile is not None:
            light_tmp_path = _write_upload_to_temp(lightFile)
            light_reader_type = infer_reader_type(light_tmp_path)
            if light_reader_type == "csv":
                light_preview = {
                    "light_preview_available": False,
                    "light_preview": [],
                }
            else:
                light_raw = load_native_file(light_tmp_path, light_reader_type)
                light_preview = build_light_preview(raw=light_raw, resample_freq=resampleFreq)

        merged = {
            **preview,
            **light_preview,
            "detected_input_type": reader_type,
        }

        return JSONResponse(content=merged)

    except ValueError as e:
        return JSONResponse(status_code=400, content={"detail": str(e)})
    except Exception as e:
        return JSONResponse(status_code=500, content={"detail": f"Server error: {str(e)}"})