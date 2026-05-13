from typing import Optional, List
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
    build_light_rgb_preview,
    manipulate_light_data,
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
    maskingFiles: Optional[List[UploadFile]] = File(None),
    sleepDiaryFiles: Optional[List[UploadFile]] = File(None),
    startStopFiles: Optional[List[UploadFile]] = File(None),
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
    maskingFiles: Optional[List[UploadFile]] = File(None),
    sleepDiaryFiles: Optional[List[UploadFile]] = File(None),
    startStopFiles: Optional[List[UploadFile]] = File(None),
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

@app.post("/api/light/rgb-preview")
async def preview_light_rgb(
    file: UploadFile = File(...),
    resampleFreq: str = Form("5min"),
):
    try:
        tmp_path = _write_upload_to_temp(file)
        raw, reader_type = _load_native_supported_file(tmp_path)

        payload = build_light_rgb_preview(raw=raw, resample_freq=resampleFreq)

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
    lmxLength: str = Form("5h"),
    lowest: str = Form("true"),
    binarize: str = Form("false"),
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
            lmx_length=lmxLength,
            lowest=str(lowest).lower() == "true",
            binarize=str(binarize).lower() == "true",
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



@app.post("/api/light/manipulate")
async def manipulate_light(
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
    try:
        tmp_path = _write_upload_to_temp(file)
        raw, reader_type = _load_native_supported_file(tmp_path)

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


def _apply_support_file_logic(raw, masking_paths=None, diary_paths=None, start_stop_paths=None):
    import pandas as pd

    summary = {
        "masking_files_received": len(masking_paths or []),
        "sleep_diary_files_received": len(diary_paths or []),
        "start_stop_files_received": len(start_stop_paths or []),
        "mask_intervals_applied": 0,
        "sleep_diary_rows_loaded": 0,
        "start_stop_applied": False,
        "notes": [],
    }

    def apply_interval(start, stop, source):
        if start is None or stop is None:
            return
        try:
            start_ts = pd.to_datetime(start)
            stop_ts = pd.to_datetime(stop)
            if hasattr(raw, "add_mask_period"):
                raw.add_mask_period(start=start_ts, stop=stop_ts)
                summary["mask_intervals_applied"] += 1
            elif hasattr(raw, "mask") and hasattr(raw, "data") and raw.data is not None:
                raw.data.loc[start_ts:stop_ts] = pd.NA
                summary["mask_intervals_applied"] += 1
            else:
                summary["notes"].append(f"{source}: interval parsed but this raw object does not expose add_mask_period or editable raw.data.")
        except Exception as exc:
            summary["notes"].append(f"{source}: could not apply interval ({exc}).")

    # 1) Apply start/stop first, because pyActigraphy's SST-log use case is to remove
    #    leading/trailing periods when the device was not yet worn or no longer worn.
    for path in start_stop_paths or []:
        df = _read_support_table(path)
        start_col = _find_column(df, ["start", "start_time", "startTime", "onset", "begin", "Start_time"])
        stop_col = _find_column(df, ["stop", "end", "end_time", "stopTime", "offset", "Stop_time"])
        if df is not None and len(df) > 0 and start_col and stop_col:
            start = pd.to_datetime(df.iloc[0][start_col])
            stop = pd.to_datetime(df.iloc[0][stop_col])
            if hasattr(raw, "data") and raw.data is not None:
                try:
                    raw.data = raw.data.loc[start:stop]
                    summary["start_stop_applied"] = True
                    summary["notes"].append("Start/stop interval applied before masking and sleep scoring.")
                except Exception as exc:
                    summary["notes"].append(f"Start/stop file parsed but data truncation failed ({exc}).")
            else:
                summary["notes"].append("Start/stop file parsed, but raw.data is not available.")
        else:
            summary["notes"].append("Start/stop file received, but start/stop columns were not recognized.")

    # 2) Apply masks after truncation.
    for path in masking_paths or []:
        df = _read_support_table(path)
        start_col = _find_column(df, ["start", "start_time", "startTime", "onset", "begin", "Start_time"])
        stop_col = _find_column(df, ["stop", "end", "end_time", "stopTime", "offset", "Stop_time"])
        if df is not None and start_col and stop_col:
            for _, row in df.iterrows():
                apply_interval(row[start_col], row[stop_col], "masking")
        else:
            summary["notes"].append("Masking file received, but start/stop columns were not recognized.")

    # 3) Load diary metadata last so downstream sleep summaries can use the cleaned/truncated signal.
    for path in diary_paths or []:
        df = _read_support_table(path)
        if df is not None:
            summary["sleep_diary_rows_loaded"] += int(len(df))
            if hasattr(raw, "read_sleep_diary"):
                try:
                    raw.read_sleep_diary(path)
                    summary["notes"].append("Sleep diary loaded with raw.read_sleep_diary.")
                except Exception as exc:
                    summary["notes"].append(f"Sleep diary parsed but raw.read_sleep_diary failed ({exc}).")
            else:
                summary["notes"].append("Sleep diary parsed; this raw object does not expose read_sleep_diary.")
        else:
            summary["notes"].append("Sleep diary file received but could not be parsed.")

    return summary

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
    maskingFiles: Optional[List[UploadFile]] = File(None),
    sleepDiaryFiles: Optional[List[UploadFile]] = File(None),
    startStopFiles: Optional[List[UploadFile]] = File(None),
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

        masking_paths = [_write_upload_to_temp(item) for item in (maskingFiles or [])]
        diary_paths = [_write_upload_to_temp(item) for item in (sleepDiaryFiles or [])]
        start_stop_paths = [_write_upload_to_temp(item) for item in (startStopFiles or [])]
        support_file_summary = _apply_support_file_logic(
            raw,
            masking_paths=masking_paths,
            diary_paths=diary_paths,
            start_stop_paths=start_stop_paths,
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
                "supportFileSummary": support_file_summary,
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