from typing import Optional
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import json
import tempfile
from pathlib import Path

from .analysis import run_basic_pyactigraphy_analysis, build_native_preview, build_light_preview
from .qc import quick_qc
from .io_helpers import (
    load_native_file,
    infer_reader_type,
    load_custom_tabular,
    load_auto_tabular,
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
        tmp.write(upload.file.read())
        return tmp.name


def _json_or_empty(value):
    try:
        return json.loads(value or "{}")
    except Exception:
        return {}


def _load_raw_or_tabular(file_path, original_name, csv_mapping, csv_separator):
    reader_type = infer_reader_type(file_path)

    if reader_type == "tabular":
        has_manual_mapping = bool(csv_mapping.get("timestamp_col")) and bool(csv_mapping.get("activity_col"))
        if has_manual_mapping:
            mapped_df = load_custom_tabular(
                file_path=file_path,
                timestamp_col=csv_mapping.get("timestamp_col"),
                activity_col=csv_mapping.get("activity_col"),
                light_col=csv_mapping.get("light_col") or None,
                temperature_col=csv_mapping.get("temperature_col") or None,
                nonwear_col=csv_mapping.get("nonwear_col") or None,
                sep=csv_separator,
            )
        else:
            mapped_df, csv_mapping = load_auto_tabular(file_path, sep=csv_separator)

        raw = build_baseraw_from_dataframe(mapped_df, name=original_name)
        return raw, reader_type, csv_mapping

    raw = load_native_file(file_path, reader_type)
    return raw, reader_type, {}


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
        csv_mapping = _json_or_empty(csvMapping)

        tmp_path = _write_upload_to_temp(file)
        raw, reader_type, resolved_mapping = _load_raw_or_tabular(
            tmp_path, file.filename, csv_mapping, csvSeparator
        )

        preview = build_native_preview(raw=raw, activity_channel=activityChannel, resample_freq=resampleFreq)
        light_preview = build_light_preview(raw=raw, resample_freq=resampleFreq)

        if (not light_preview.get("light_preview_available")) and lightFile is not None:
            light_tmp = _write_upload_to_temp(lightFile)
            light_raw, _, _ = _load_raw_or_tabular(light_tmp, lightFile.filename, {}, csvSeparator)
            light_preview = build_light_preview(raw=light_raw, resample_freq=resampleFreq)

        return JSONResponse(
            content={
                **preview,
                **light_preview,
                "detected_input_type": reader_type,
                "resolved_csv_mapping": resolved_mapping,
            }
        )

    except ValueError as e:
        return JSONResponse(status_code=400, content={"detail": str(e)})
    except Exception as e:
        return JSONResponse(status_code=500, content={"detail": "Server error: {}".format(str(e))})


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
        csv_mapping = _json_or_empty(csvMapping)

        tmp_path = _write_upload_to_temp(file)
        raw, reader_type, resolved_mapping = _load_raw_or_tabular(
            tmp_path, file.filename, csv_mapping, csvSeparator
        )

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
                "resolved_csv_mapping": resolved_mapping,
            }
        )

    except ValueError as e:
        return JSONResponse(status_code=400, content={"detail": str(e)})
    except Exception as e:
        return JSONResponse(status_code=500, content={"detail": "Server error: {}".format(str(e))})