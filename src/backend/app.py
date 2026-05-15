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

from .accelerometer_loader import (
    convert_bin_lightweight_summary,
    summarize_uploaded_accelerometer_csv,
    MAX_SERVER_SIDE_BIN_MB,
    DEFAULT_JAVA_HEAP_MB,
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
            "pyActigraphy-supported format. For .bin/.cwa files, use the lightweight converter for "
            "small demo files or upload a pre-converted accelerometer *timeSeries.csv.gz file."
        )

    raw = load_native_file(file_path, reader_type)
    return raw, reader_type


@app.post("/api/accelerometer/convert-lite")
async def convert_accelerometer_lite(
    file: UploadFile = File(...),
    epochPeriod: int = Form(30),
    javaHeapMb: int = Form(DEFAULT_JAVA_HEAP_MB),
):
    """Lightweight diagnostic endpoint for small raw .bin/.cwa files or uploaded timeSeries CSVs.

    This returns a compact summary rather than running the full pyActigraphy analysis.
    It is useful on low-memory Render instances to confirm that the conversion/loading path works.
    """
    try:
        tmp_path = _write_upload_to_temp(file)
        suffix = Path(file.filename or tmp_path).suffix.lower()

        if suffix in (".bin", ".cwa"):
            payload = convert_bin_lightweight_summary(
                tmp_path,
                epoch_period=epochPeriod,
                java_heap_mb=javaHeapMb,
            )
            mode = "server_side_raw_conversion_limited"
        else:
            payload = summarize_uploaded_accelerometer_csv(tmp_path, epoch_period=epochPeriod)
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




def _extract_sleep_windows_from_table(df):
    import pandas as pd

    windows = []
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
            start = pd.to_datetime(row[start_col])
            stop = pd.to_datetime(row[stop_col])
            if pd.isna(start) or pd.isna(stop) or stop <= start:
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


def _read_sleep_diary_table(file_path: str):
    # pyActigraphy sleep diaries often include a small preamble before the table;
    # try normal parsing first, then retry with skipped header rows.
    df = _read_support_table(file_path)
    if df is not None and _extract_sleep_windows_from_table(df):
        return df

    try:
        import pandas as pd
        for skiprows in range(1, 6):
            try:
                candidate = pd.read_csv(file_path, skiprows=skiprows)
                if _extract_sleep_windows_from_table(candidate):
                    return candidate
            except Exception:
                try:
                    candidate = pd.read_csv(file_path, sep=None, engine="python", skiprows=skiprows)
                    if _extract_sleep_windows_from_table(candidate):
                        return candidate
                except Exception:
                    pass
    except Exception:
        pass

    return df

def _apply_support_file_logic(raw, masking_paths=None, diary_paths=None, start_stop_paths=None, support_settings=None):
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

    def apply_start_stop_window(start, stop, source="start/stop"):
        try:
            start = pd.to_datetime(start)
            stop = pd.to_datetime(stop)
            if pd.isna(start) or pd.isna(stop) or stop <= start:
                summary["notes"].append(f"{source}: skipped invalid start/stop interval.")
                return
            if hasattr(raw, "data") and raw.data is not None:
                raw.data = raw.data.loc[start:stop]
                summary["start_stop_applied"] = True
                summary["notes"].append(f"{source}: applied recording interval before masking and sleep scoring.")
            else:
                summary["notes"].append(f"{source}: parsed, but raw.data is not available.")
        except Exception as exc:
            summary["notes"].append(f"{source}: data truncation failed ({exc}).")

    # 1) Apply start/stop first, because pyActigraphy's SST-log use case is to remove
    #    leading/trailing periods when the device was not yet worn or no longer worn.
    if start_stop_settings.get("apply", True):
        for interval in start_stop_settings.get("manualIntervals", []) or []:
            apply_start_stop_window(interval.get("start"), interval.get("stop"), "manual start/stop")

    for path in (start_stop_paths or []) if start_stop_settings.get("apply", True) else []:
        df = _read_support_table(path)
        start_col = _find_column(df, ["start", "start_time", "startTime", "onset", "begin", "Start_time"])
        stop_col = _find_column(df, ["stop", "end", "end_time", "stopTime", "offset", "Stop_time"])
        if df is not None and len(df) > 0 and start_col and stop_col:
            start = pd.to_datetime(df.iloc[0][start_col])
            stop = pd.to_datetime(df.iloc[0][stop_col])
            apply_start_stop_window(start, stop, "start/stop file")
        else:
            summary["notes"].append("Start/stop file received, but start/stop columns were not recognized.")

    # 2) Apply masks after truncation.
    if masking_settings.get("apply", True):
        for interval in masking_settings.get("manualIntervals", []) or []:
            apply_interval(interval.get("start"), interval.get("stop"), "manual masking")

    for path in (masking_paths or []) if masking_settings.get("apply", True) else []:
        df = _read_support_table(path)
        start_col = _find_column(df, ["start", "start_time", "startTime", "onset", "begin", "Start_time"])
        stop_col = _find_column(df, ["stop", "end", "end_time", "stopTime", "offset", "Stop_time"])
        if df is not None and start_col and stop_col:
            for _, row in df.iterrows():
                apply_interval(row[start_col], row[stop_col], "masking")
        else:
            summary["notes"].append("Masking file received, but start/stop columns were not recognized.")

    # 3) Load diary metadata last so downstream sleep summaries can use the cleaned/truncated signal.
    sleep_windows = []
    if diary_settings.get("apply", True):
        for interval in diary_settings.get("manualIntervals", []) or []:
            try:
                start = pd.to_datetime(interval.get("start"))
                stop = pd.to_datetime(interval.get("stop"))
                if pd.isna(start) or pd.isna(stop) or stop <= start:
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
        df = _read_sleep_diary_table(path)
        if df is not None:
            summary["sleep_diary_rows_loaded"] += int(len(df))
            windows = _extract_sleep_windows_from_table(df)
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
        sleep_window_settings = analysis_config.get("sleepWindowSettings", {})
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
            support_settings=analysis_config.get("supportFileSettings", {}),
        )

        results = run_basic_pyactigraphy_analysis(
            raw=raw,
            metric_requests=metric_requests,
            family_requests=family_requests,
            analysis_scope=analysis_scope,
            algorithm_request=algorithm_request,
            sleep_window_settings=sleep_window_settings,
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