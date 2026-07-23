import copy
import math
import numbers
import pandas as pd

from .diagnostics import (
    diagnostic_stage,
    mark_current_stage,
    record_suppressed_exception,
    result_summary,
    update_current_stage,
)


def _get_light_recording(raw):
    light_obj = getattr(raw, "light", None)
    if light_obj is None or not hasattr(light_obj, "get_channel_list"):
        return None
    return light_obj


def _get_light_channels(raw):
    light_obj = _get_light_recording(raw)
    if light_obj is None:
        return []
    try:
        return [str(c) for c in light_obj.get_channel_list()]
    except Exception:
        return []


def _pick_default_light_channel(channels):
    if not channels:
        return None
    lowered = {c.lower(): c for c in channels}
    for preferred in ["weißes licht", "weisses licht", "white light", "whitelight", "light", "amb light"]:
        if preferred in lowered:
            return lowered[preferred]
    return channels[0]




def _normalize_light_time_arg(value):
    if value is None or value == "":
        return None
    text = str(value).strip()
    if not text:
        return None
    if "T" in text or ("-" in text and ":" in text):
        parsed = pd.to_datetime(text, errors="coerce")
        if parsed is not pd.NaT and not pd.isna(parsed):
            return parsed.strftime("%H:%M:%S")
    if len(text) == 5 and text.count(":") == 1:
        return text + ":00"
    return text


def _clock_seconds(value):
    if value is None or value == "":
        return None
    try:
        t = pd.to_datetime(str(value)).time()
        return int(t.hour) * 3600 + int(t.minute) * 60 + int(getattr(t, "second", 0))
    except Exception:
        return None


def _clock_window_crosses_midnight(start_time, stop_time):
    start_seconds = _clock_seconds(start_time)
    stop_seconds = _clock_seconds(stop_time)
    return start_seconds is not None and stop_seconds is not None and stop_seconds < start_seconds


def _filter_series_by_clock_window(series, start_time=None, stop_time=None):
    if series is None:
        return None
    if start_time is None and stop_time is None:
        return series
    if not isinstance(series.index, pd.DatetimeIndex):
        return series
    start_seconds = _clock_seconds(start_time)
    stop_seconds = _clock_seconds(stop_time)
    if start_seconds is None and stop_seconds is None:
        return series

    seconds = series.index.hour * 3600 + series.index.minute * 60 + series.index.second
    if start_seconds is None:
        mask = seconds <= stop_seconds
    elif stop_seconds is None:
        mask = seconds >= start_seconds
    elif stop_seconds >= start_seconds:
        mask = (seconds >= start_seconds) & (seconds <= stop_seconds)
    else:
        # Overnight clock window, e.g. 23:00 -> 02:00.
        mask = (seconds >= start_seconds) | (seconds <= stop_seconds)
    return series.loc[mask]


def _format_output_minutes(minutes, oformat):
    fmt = str(oformat or "minute").lower()
    if fmt.startswith("hour") or fmt in {"h", "hr", "hrs"}:
        return minutes / 60.0
    if fmt.startswith("day") or fmt in {"d"}:
        return minutes / (60.0 * 24.0)
    return minutes


def _aggregate_series(series, agg):
    if series is None or len(series) == 0:
        return None
    method = str(agg or "mean").lower()
    if method == "median":
        return series.median()
    if method == "sum":
        return series.sum()
    if method in {"std", "sd"}:
        return series.std()
    if method == "min":
        return series.min()
    if method == "max":
        return series.max()
    return series.mean()


def _run_light_clock_window_metric(raw, metric_id, channel=None, threshold=None, start_time=None, stop_time=None, agg="mean", oformat="minute"):
    channels = _get_light_channels(raw)
    if not channels:
        raise ValueError("No light channels are available on the loaded file.")
    selected_channels = [channel] if channel else channels
    values = {}

    for ch in selected_channels:
        series = _get_light_channel_series(raw, ch)
        if series is None or len(series) == 0:
            values[ch] = None
            continue
        window_series = _filter_series_by_clock_window(series, start_time=start_time, stop_time=stop_time)
        window_series = _coerce_series_to_numeric(window_series)
        if window_series is None or len(window_series) == 0:
            values[ch] = None
            continue

        if metric_id == "exposure_level":
            metric_series = window_series
            if threshold is not None:
                metric_series = metric_series[metric_series >= threshold]
            values[ch] = _aggregate_series(metric_series, agg)
        elif metric_id in {"tat", "tatp"}:
            if threshold is None:
                raise ValueError(f"{metric_id.upper()} requires a lux threshold.")
            above = window_series >= threshold
            if metric_id == "tat":
                minutes = float(above.sum()) * _epoch_minutes(window_series.index)
                values[ch] = _format_output_minutes(minutes, oformat)
            else:
                values[ch] = float(above.mean()) * 100.0 if len(above) else None

    if channel:
        return values.get(channel)
    return pd.Series(values, name=metric_id)

def _lux_to_log10_threshold(threshold_lux):
    if threshold_lux is None or threshold_lux == "":
        return None
    try:
        lux = float(threshold_lux)
    except Exception:
        return None
    if lux < 0:
        return None
    return math.log10(lux + 1.0)


def _serialize_scalar(value, ndigits=2):
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except Exception:
        pass
    if isinstance(value, bool):
        return value
    if isinstance(value, numbers.Number):
        value = float(value)
        if math.isfinite(value):
            return round(value, ndigits)
        return None
    if isinstance(value, str):
        return value
    try:
        numeric = float(value)
        if math.isfinite(numeric):
            return round(numeric, ndigits)
    except Exception:
        return str(value)
    return str(value)


def _serialize_series(series):
    return {"kind": "series", "index": [str(i) for i in series.index.tolist()], "values": [_serialize_scalar(v) for v in series.tolist()], "name": str(series.name) if series.name is not None else None}


def _serialize_dataframe(df):
    if isinstance(df.columns, pd.MultiIndex):
        columns = [" | ".join([str(x) for x in col if x is not None]) for col in df.columns.tolist()]
    else:
        columns = [str(c) for c in df.columns.tolist()]
    rows = []
    for idx, row in df.iterrows():
        rows.append({"index": str(idx), "values": [_serialize_scalar(v) for v in row.tolist()]})
    return {"kind": "dataframe", "columns": columns, "rows": rows}


def _select_channel_from_result(result, channel):
    if channel is None:
        return result
    if isinstance(result, pd.Series):
        if channel in result.index:
            return result.loc[channel]
        return result
    if isinstance(result, pd.DataFrame):
        if "channel" in result.columns:
            filtered = result[result["channel"].astype(str) == str(channel)]
            if not filtered.empty:
                return filtered
        if isinstance(result.columns, pd.MultiIndex):
            if channel in result.columns.get_level_values(0):
                return result[channel]
        elif channel in result.columns:
            return result[channel]
        return result
    return result


def _values_by_channel(df):
    if isinstance(df, pd.DataFrame) and "channel" in df.columns and "value" in df.columns:
        return df.set_index("channel")["value"]
    return pd.Series(dtype=float)


def run_basic_pylight_analysis(raw, metric_id, channel=None, threshold_lux=None, start_time=None, stop_time=None, bins="24h", agg="mean", agg_funcs=None, oformat="minute", lmx_length="5h", lowest=True, binarize=False):
    light_obj = _get_light_recording(raw)
    if light_obj is None:
        raise ValueError("No light recording is available on the loaded file.")
    channels = _get_light_channels(raw)
    if not channels:
        raise ValueError("No light channels are available on the loaded file.")
    if channel is None:
        channel = _pick_default_light_channel(channels)
    threshold = _lux_to_log10_threshold(threshold_lux)
    start_time = _normalize_light_time_arg(start_time)
    stop_time = _normalize_light_time_arg(stop_time)
    crosses_midnight = _clock_window_crosses_midnight(start_time, stop_time)

    if crosses_midnight and metric_id in {"exposure_level", "tat", "tatp"}:
        # pyActigraphy light functions are not guaranteed to interpret start_time > stop_time
        # as an overnight window. Use an explicit clock-time mask so 23:00 -> 02:00
        # means time >= 23:00 OR time <= 02:00.
        result = _run_light_clock_window_metric(
            raw,
            metric_id=metric_id,
            channel=channel,
            threshold=threshold,
            start_time=start_time,
            stop_time=stop_time,
            agg=agg or "mean",
            oformat=oformat or "minute",
        )
    elif metric_id == "exposure_level":
        result = light_obj.light_exposure_level(threshold=threshold, start_time=start_time or None, stop_time=stop_time or None, agg=agg or "mean")
        result = _select_channel_from_result(result, channel)
    elif metric_id == "summary_stats":
        result = light_obj.summary_statistics_per_time_bin(bins=bins or "24h", agg_func=agg_funcs or ["mean", "median", "sum", "std", "min", "max"])
        result = _select_channel_from_result(result, channel)
    elif metric_id == "tat":
        result = light_obj.TAT(threshold=threshold, start_time=start_time or None, stop_time=stop_time or None, oformat=oformat or "minute")
        result = _select_channel_from_result(result, channel)
    elif metric_id == "tatp":
        result = light_obj.TATp(threshold=threshold, start_time=start_time or None, stop_time=stop_time or None, oformat=oformat or "minute")
        result = _select_channel_from_result(result, channel)
    elif metric_id == "mlit":
        if threshold is None:
            raise ValueError("MLiT requires a lux threshold such as 10, 100, or 500.")
        result = light_obj.MLiT(threshold=threshold)
        result = _select_channel_from_result(result, channel)
    elif metric_id == "extremum_min":
        result = light_obj.get_light_extremum(extremum="min")
        result = _select_channel_from_result(result, channel)
    elif metric_id == "extremum_max":
        result = light_obj.get_light_extremum(extremum="max")
        result = _select_channel_from_result(result, channel)
    elif metric_id in {"l5", "m10"}:
        result = light_obj.LMX(length="5h" if metric_id == "l5" else "10h", lowest=(metric_id == "l5"))
        result = _select_channel_from_result(result, channel)
    elif metric_id == "lmx":
        result = light_obj.LMX(length=lmx_length or "5h", lowest=bool(lowest))
        result = _select_channel_from_result(result, channel)
    elif metric_id == "is":
        result = light_obj.IS(binarize=bool(binarize), threshold=threshold or 0)
        result = _select_channel_from_result(result, channel)
    elif metric_id == "iv":
        result = light_obj.IV(binarize=bool(binarize), threshold=threshold or 0)
        result = _select_channel_from_result(result, channel)
    elif metric_id == "ra":
        l5_values = _values_by_channel(light_obj.LMX(length="5h", lowest=True))
        m10_values = _values_by_channel(light_obj.LMX(length="10h", lowest=False))
        common = [ch for ch in m10_values.index if ch in l5_values.index]
        result = pd.Series({ch: ((m10_values.loc[ch] - l5_values.loc[ch]) / (m10_values.loc[ch] + l5_values.loc[ch]) if (m10_values.loc[ch] + l5_values.loc[ch]) != 0 else None) for ch in common}, name="RA")
        result = _select_channel_from_result(result, channel)
    elif metric_id == "vat":
        if threshold is None:
            raise ValueError("VAT requires a lux threshold such as 10 or 100.")
        result = light_obj.VAT(threshold)
        result = _select_channel_from_result(result, channel)
    else:
        raise ValueError("Unsupported light metric '{}'.".format(metric_id))

    if isinstance(result, pd.DataFrame):
        payload = _serialize_dataframe(result)
    elif isinstance(result, pd.Series):
        payload = _serialize_series(result)
    else:
        payload = {"kind": "scalar", "value": _serialize_scalar(result)}
    return {
        "metric_id": metric_id,
        "channel": channel,
        "available_channels": channels,
        "threshold_lux": _serialize_scalar(threshold_lux),
        "threshold_log10": _serialize_scalar(threshold),
        "start_time": start_time,
        "stop_time": stop_time,
        "time_window_crossed_midnight": bool(crosses_midnight),
        "result": payload,
    }


def get_basic_light_channels(raw):
    channels = _get_light_channels(raw)
    return {"channels": channels, "default_channel": _pick_default_light_channel(channels)}


def _light_dataframe(raw, channels=None):
    requested = channels or _get_light_channels(raw)
    series_map = {}
    for channel in requested:
        series = _get_light_channel_series(raw, channel)
        if series is not None and len(series) > 0:
            series_map[channel] = series.rename(channel)
    if not series_map:
        raise ValueError("No usable light channel data were found.")
    return pd.concat(series_map.values(), axis=1).sort_index()


def manipulate_light_data(raw, channels=None, truncate_start=None, truncate_stop=None, daily_start_time=None, daily_stop_time=None, resample_freq=None, binarize=False, threshold_lux=None, filter_method="none", filter_window="15min", max_points=1200):
    df = _light_dataframe(raw, channels=channels)
    original_rows = len(df)
    if truncate_start:
        df = df.loc[pd.to_datetime(truncate_start):]
    if truncate_stop:
        df = df.loc[:pd.to_datetime(truncate_stop)]
    if daily_start_time and daily_stop_time:
        start = pd.to_datetime(daily_start_time).time()
        stop = pd.to_datetime(daily_stop_time).time()
        times = df.index.time
        if start <= stop:
            mask = [(t >= start and t <= stop) for t in times]
        else:
            mask = [(t >= start or t <= stop) for t in times]
        df = df.loc[mask]
    if resample_freq:
        df = df.resample(resample_freq).mean()
    if filter_method in {"mean", "median"}:
        rolled = df.rolling(filter_window, min_periods=1)
        df = rolled.mean() if filter_method == "mean" else rolled.median()
    threshold = _lux_to_log10_threshold(threshold_lux)
    if binarize:
        if threshold is None:
            raise ValueError("Binarization requires a lux threshold.")
        df = (df > threshold).astype(int)
    df = df.dropna(how="all")
    return {"light_manipulation_available": True, "channels": list(df.columns), "summary": {"original_rows": int(original_rows), "rows": int(len(df)), "start": str(df.index.min()) if len(df) else None, "end": str(df.index.max()) if len(df) else None, "threshold_lux": _serialize_scalar(threshold_lux), "threshold_log10": _serialize_scalar(threshold), "resample_freq": resample_freq, "filter_method": filter_method, "filter_window": filter_window, "binarized": bool(binarize)}, "preview": _sample_multichannel_dataframe(df, max_points=max_points)}

DEFAULT_MEAN_FREQS = [
    "1min", "2min", "3min", "4min", "5min", "6min", "8min", "9min", "10min",
    "12min", "15min", "16min", "18min", "20min", "24min", "30min", "32min",
    "36min", "40min", "45min", "48min", "60min",
]

ALGO_TO_SRI_KEY = {
    "cole_kripke": "CK",
    "sadeh": "Sadeh",
    "oakley": "Oakley",
    "scripps": "Scripps",
    "crespo": "Crespo",
    "roenneberg": "Roenneberg",
}

IMPLEMENTED_FAMILY_METRICS = {
    "amplitude": ["ra", "rap"],
    "rhythm": ["is", "iv", "ism", "ivm", "isp", "ivp"],
    "sleep": ["sri", "tst", "waso", "sleep_efficiency"],
    "fragmentation": ["kra", "kar"],
}

ADVANCED_FAMILY_IDS = {"cosinor", "flm", "mfdfa", "ssa", "clustering"}


def _safe_float(value):
    try:
        number = float(value)
        return number if math.isfinite(number) else None
    except Exception:
        return None


def _safe_call(callable_obj, *args, **kwargs):
    try:
        return callable_obj(*args, **kwargs)
    except Exception as exc:
        operation = getattr(callable_obj, "__qualname__", None) or getattr(callable_obj, "__name__", None) or str(callable_obj)
        record_suppressed_exception(operation, exc, note="Exception was previously converted to None by _safe_call.")
        return None


def _value_to_numeric_scalar(value):
    try:
        if pd.isna(value):
            return None
    except Exception:
        pass
    if isinstance(value, (list, tuple, set)):
        vals = []
        for item in value:
            try:
                vals.append(float(item))
            except Exception:
                continue
        if not vals:
            return None
        # Multi-axis accelerometer rows are reduced to vector magnitude so pandas
        # comparisons like series > 0 do not fail with shape-mismatch errors.
        return math.sqrt(sum(item * item for item in vals))
    try:
        # numpy arrays and pandas extension arrays expose tolist().
        if hasattr(value, "tolist") and not isinstance(value, (str, bytes)):
            return _value_to_numeric_scalar(value.tolist())
    except Exception:
        pass
    try:
        return float(value)
    except Exception:
        return None


def _coerce_series_to_numeric(series):
    if series is None:
        return None
    if isinstance(series, pd.DataFrame):
        numeric_cols = series.select_dtypes(include="number").columns.tolist()
        if numeric_cols:
            preferred = ["VM", "vm", "activity", "Activity", "data", "light"]
            chosen = next((col for col in preferred if col in numeric_cols), numeric_cols[0])
            series = series[chosen]
        elif series.shape[1] > 0:
            series = series.iloc[:, 0]
        else:
            return None
    if not isinstance(series, pd.Series):
        try:
            series = pd.Series(series)
        except Exception:
            return None
    try:
        numeric = pd.to_numeric(series, errors="coerce")
    except Exception:
        numeric = series.map(_value_to_numeric_scalar)
        numeric = pd.to_numeric(numeric, errors="coerce")
    if numeric.dropna().empty and len(series.dropna()) > 0:
        numeric = series.map(_value_to_numeric_scalar)
        numeric = pd.to_numeric(numeric, errors="coerce")
    numeric = numeric.dropna()
    return numeric.sort_index() if len(numeric) else None


def _get_activity_series(raw, preferred_channel=None):
    data = getattr(raw, "data", None)
    if data is None:
        return None
    if isinstance(data, pd.DataFrame):
        cols = list(data.columns)
        preferred = [preferred_channel, "VM", "vm", "activity", "Activity", "data", "counts", "acc"]
        for col in preferred:
            if col and col in cols:
                return _coerce_series_to_numeric(data[col])
        numeric_cols = data.select_dtypes(include="number").columns.tolist()
        if len(numeric_cols) >= 3:
            # If x/y/z columns are present, use vector magnitude rather than a single axis.
            frame = data[numeric_cols[:3]].apply(pd.to_numeric, errors="coerce")
            magnitude = (frame.pow(2).sum(axis=1).pow(0.5)).rename("VM")
            return _coerce_series_to_numeric(magnitude)
        if numeric_cols:
            return _coerce_series_to_numeric(data[numeric_cols[0]])
        if cols:
            return _coerce_series_to_numeric(data[cols[0]])
        return None
    return _coerce_series_to_numeric(data)


def _json_ready_metric_value(value, depth=0):
    """Convert pyActigraphy/Pandas/NumPy results into JSON-safe values.

    Periodic metrics such as ISp, IVp, and RAp may return NumPy arrays,
    Pandas objects, tuples, or NumPy scalar types rather than a single Python
    float. Returning those objects directly causes Starlette's JSONResponse to
    raise *after* the endpoint try/except block, resulting in a plain-text HTTP
    500 with no structured diagnostics.
    """
    if depth > 8:
        return str(value)
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, numbers.Number):
        try:
            number = float(value)
            return number if math.isfinite(number) else None
        except Exception:
            return None
    if isinstance(value, str):
        return value
    if isinstance(value, (pd.Timestamp, pd.Timedelta)):
        return value.isoformat() if isinstance(value, pd.Timestamp) else str(value)
    if isinstance(value, pd.Series):
        return [_json_ready_metric_value(item, depth + 1) for item in value.tolist()]
    if isinstance(value, pd.DataFrame):
        return [
            {str(key): _json_ready_metric_value(item, depth + 1) for key, item in row.items()}
            for row in value.to_dict(orient="records")
        ]
    if isinstance(value, dict):
        return {str(key): _json_ready_metric_value(item, depth + 1) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_json_ready_metric_value(item, depth + 1) for item in value]
    try:
        if hasattr(value, "tolist"):
            return _json_ready_metric_value(value.tolist(), depth + 1)
    except Exception:
        pass
    try:
        if hasattr(value, "item"):
            return _json_ready_metric_value(value.item(), depth + 1)
    except Exception:
        pass
    try:
        number = float(value)
        return number if math.isfinite(number) else None
    except Exception:
        return str(value)


def _resolve_series_to_numeric(value):
    return _json_ready_metric_value(value)


def _call_raw_method(raw, method_name, *args, **kwargs):
    method = getattr(raw, method_name, None)
    if method is None or not callable(method):
        return None
    return _safe_call(method, *args, **kwargs)


def _normalize_sleep_score_convention(scored, algorithm):
    """Return binary scores using the app convention 1=sleep/rest, 0=wake.

    pyActigraphy's Crespo output uses 1 for active and 0 for rest, whereas
    Roenneberg and the app's downstream sleep summaries use 1 for sleep/rest.
    """
    if scored is None:
        return None
    if algorithm != "crespo":
        return scored
    try:
        if isinstance(scored, pd.DataFrame):
            return 1 - scored.apply(pd.to_numeric, errors="coerce")
        if isinstance(scored, pd.Series):
            return (1 - pd.to_numeric(scored, errors="coerce")).rename(scored.name)
        return 1 - scored
    except Exception:
        return scored


def _score_algorithm(raw, algorithm, algorithm_params=None):
    algorithm_params = algorithm_params or {}
    params = algorithm_params.get(algorithm, {}) if isinstance(algorithm_params, dict) else {}

    if algorithm == "cole_kripke":
        method = getattr(raw, "CK", None)
        if method is None or not callable(method):
            return None
        settings = params.get("settings") or "30sec_max_non_overlap"
        threshold = params.get("threshold", 1.0)
        rescoring = params.get("rescoring", True)
        attempts = [
            {"settings": settings, "threshold": threshold, "rescoring": rescoring},
            {"settings": "mean", "threshold": threshold, "rescoring": rescoring},
            {},
        ]
        seen = set()
        for kwargs in attempts:
            key = tuple(sorted(kwargs.items()))
            if key in seen:
                continue
            seen.add(key)
            try:
                return method(**kwargs)
            except Exception:
                continue
        return None
    if algorithm == "sadeh":
        return _call_raw_method(raw, "Sadeh")
    if algorithm == "scripps":
        return _call_raw_method(raw, "Scripps")
    if algorithm == "oakley":
        threshold_mode = params.get("thresholdMode", ["auto"])
        if isinstance(threshold_mode, str):
            threshold_mode = [threshold_mode]
        mode = threshold_mode[0] if threshold_mode else "auto"
        threshold = "automatic" if mode == "auto" else params.get("manualThreshold", 40)
        return _call_raw_method(raw, "Oakley", threshold=threshold)
    if algorithm == "crespo":
        method = getattr(raw, "Crespo", None)
        if method is None or not callable(method):
            return None
        kwargs = {}
        for key in ["zeta", "zeta_r", "zeta_a", "t", "alpha", "beta", "estimate_zeta", "seq_length_max", "verbose"]:
            if key in params and params[key] not in (None, ""):
                kwargs[key] = params[key]
        scored = _safe_call(method, **kwargs) if kwargs else None
        if scored is not None:
            return _normalize_sleep_score_convention(scored, "crespo")
        alpha_mode = params.get("alphaMode", "default")
        if alpha_mode == "manual":
            alpha = "{}h".format(params.get("alpha", 8))
            return _normalize_sleep_score_convention(_safe_call(method, alpha=alpha), "crespo")
        if alpha_mode == "auto":
            return _normalize_sleep_score_convention(_safe_call(method, estimate_zeta=True), "crespo")
        return _normalize_sleep_score_convention(_safe_call(method), "crespo")
    if algorithm == "roenneberg":
        method = getattr(raw, "Roenneberg", None)
        if method is None or not callable(method):
            return None
        kwargs = {}
        for key in ["trend_period", "min_trend_period", "threshold", "min_seed_period", "max_test_period", "r_consec_below", "rsfreq"]:
            if key in params and params[key] not in (None, ""):
                kwargs[key] = params[key]
        scored = _safe_call(method, **kwargs) if kwargs else None
        if scored is not None:
            return scored
        factors = params.get("thresholdFactors") or [0.15]
        factor = 0.15
        if isinstance(factors, str):
            try:
                factor = float(factors.split(",")[0].strip())
            except Exception:
                factor = 0.15
        elif isinstance(factors, list) and len(factors) > 0:
            try:
                factor = float(factors[0])
            except Exception:
                factor = 0.15
        return _safe_call(method, threshold=factor)
    return None


def _epoch_minutes(index):
    try:
        freq = getattr(index, "freq", None) or pd.infer_freq(index)
        if freq is not None:
            return pd.Timedelta(freq).total_seconds() / 60.0
    except Exception:
        pass
    try:
        diffs = pd.Series(index).diff().dropna()
        if len(diffs) > 0:
            return diffs.median().total_seconds() / 60.0
    except Exception:
        pass
    return 1.0


def _coerce_score_series(score):
    if score is None:
        return None
    if isinstance(score, pd.DataFrame):
        numeric_columns = score.select_dtypes(include="number").columns.tolist()
        if not numeric_columns:
            return None
        score = score[numeric_columns[0]]
    if not isinstance(score, pd.Series):
        try:
            score = pd.Series(score)
        except Exception:
            return None
    numeric = pd.to_numeric(score, errors="coerce").sort_index()
    return numeric if len(numeric) and numeric.notna().any() else None


def _score_rest_minutes(score):
    series = _coerce_score_series(score)
    if series is None:
        return None
    valid = series.dropna()
    if len(valid) == 0:
        return None
    return float((valid > 0).sum()) * _epoch_minutes(series.index)


def _valid_day_count(raw):
    try:
        return int(getattr(raw, "_ui_valid_day_count"))
    except Exception:
        series = _get_activity_series(raw)
        if series is None or len(series) == 0 or not isinstance(series.index, pd.DatetimeIndex):
            return 0
        return int(series.index.normalize().nunique())


def _minimum_valid_days_for_rhythm(raw):
    try:
        return max(1, int(getattr(raw, "_ui_min_valid_days_for_rhythm")))
    except Exception:
        return 2


def _activity_validity_at_score_frequency(raw, score_index):
    mask = getattr(raw, "_ui_analysis_valid_mask", None)
    if not isinstance(mask, pd.Series) or not isinstance(mask.index, pd.DatetimeIndex):
        return None
    mask = mask.astype(bool).sort_index()
    if not isinstance(score_index, pd.DatetimeIndex) or len(score_index) == 0:
        return None
    try:
        score_minutes = _epoch_minutes(score_index)
        score_frequency = pd.Timedelta(minutes=score_minutes)
        mask_frequency = pd.Timedelta(getattr(mask.index, "freq", None) or pd.infer_freq(mask.index))
        if score_frequency > mask_frequency:
            # A scored bin is valid only when every underlying activity epoch is
            # valid; this prevents partial missing bins from becoming wake.
            mask = mask.resample(score_frequency, origin="start").min().astype(bool)
    except Exception:
        pass
    return mask.reindex(score_index).fillna(False).astype(bool)


def _mask_sleep_score_with_activity(raw, score):
    series = _coerce_score_series(score)
    if series is None:
        return None
    validity = _activity_validity_at_score_frequency(raw, series.index)
    return series.where(validity) if validity is not None else series


def _missing_aware_sri(score):
    """Calculate pyActigraphy's SRI definition using only valid 24 h pairs."""

    series = _coerce_score_series(score)
    if series is None or not isinstance(series.index, pd.DatetimeIndex):
        return None
    current = series.rename("current")
    previous = series.copy()
    previous.index = previous.index + pd.Timedelta("24h")
    previous = previous.rename("previous")
    pairs = pd.concat([current, previous], axis=1, join="inner").dropna()
    if len(pairs) == 0:
        return None
    same_state_probability = float((pairs["current"] == pairs["previous"]).mean())
    return 200.0 * same_state_probability - 100.0


def _normalize_sleep_window(window, default_source="sleep_diary"):
    try:
        start = pd.to_datetime(window.get("start"))
        stop = pd.to_datetime(window.get("stop"))
        if pd.isna(start) or pd.isna(stop) or stop <= start:
            return None
        return {
            "start": start,
            "stop": stop,
            "state": str(window.get("state", "NIGHT")),
            "source": str(window.get("source", default_source)),
            "method": str(window.get("method", default_source)),
            "estimated": bool(window.get("estimated", default_source != "sleep_diary")),
        }
    except Exception:
        return None


def _get_sleep_windows(raw):
    windows = getattr(raw, "_ui_sleep_windows", None) or []
    normalized = []
    for window in windows:
        normalized_window = _normalize_sleep_window(window, default_source="sleep_diary")
        if normalized_window is not None:
            normalized.append(normalized_window)
    return normalized


def _flatten_aot_times(values):
    if values is None:
        return []
    try:
        if isinstance(values, pd.Series):
            values = values.dropna().tolist()
        elif isinstance(values, pd.DataFrame):
            values = values.stack().dropna().tolist()
    except Exception:
        pass
    if not isinstance(values, (list, tuple, set)):
        try:
            values = list(values)
        except Exception:
            values = [values]
    flattened = []
    for value in values:
        if isinstance(value, (list, tuple, set)):
            flattened.extend(_flatten_aot_times(value))
            continue
        try:
            ts = pd.to_datetime(value)
            if not pd.isna(ts):
                flattened.append(ts)
        except Exception:
            continue
    return sorted(set(flattened))


def _call_aot_method(raw, method_name, params=None):
    params = params or {}
    method = getattr(raw, method_name, None)
    if method is None or not callable(method):
        return None
    try:
        if method_name == "Crespo_AoT":
            kwargs = {}
            for key in ["zeta", "zeta_r", "zeta_a", "t", "alpha", "beta", "estimate_zeta", "seq_length_max", "verbose"]:
                if key in params and params[key] not in (None, ""):
                    kwargs[key] = params[key]
            return method(**kwargs)
        if method_name == "Roenneberg_AoT":
            kwargs = {}
            for key in [
                "trend_period",
                "min_trend_period",
                "threshold",
                "min_seed_period",
                "max_test_period",
                "r_consec_below",
                "rsfreq",
            ]:
                if key in params and params[key] not in (None, ""):
                    kwargs[key] = params[key]
            return method(**kwargs)
        return method()
    except Exception as exc:
        record_suppressed_exception(method_name, exc, note="Sleep-window AoT call failed and was previously converted to None.")
        return None


def _rest_windows_from_activity_onset_offset(onsets, offsets, min_hours=3.0, max_hours=14.0):
    onset_times = _flatten_aot_times(onsets)
    offset_times = _flatten_aot_times(offsets)
    windows = []
    if not onset_times or not offset_times:
        return windows

    for offset in offset_times:
        next_onsets = [onset for onset in onset_times if onset > offset]
        if not next_onsets:
            continue
        onset = next_onsets[0]
        duration_hours = (onset - offset).total_seconds() / 3600.0
        if min_hours <= duration_hours <= max_hours:
            windows.append({
                "start": offset,
                "stop": onset,
                "state": "ESTIMATED_REST",
                "source": "estimated_rest_period",
                "method": "activity_offset_to_next_onset",
                "estimated": True,
            })

    # Dedupe overlapping/identical windows.
    deduped = []
    seen = set()
    for window in sorted(windows, key=lambda item: item["start"]):
        key = (str(window["start"]), str(window["stop"]))
        if key in seen:
            continue
        seen.add(key)
        deduped.append(window)
    return deduped


def _format_clock_hour(hour):
    try:
        hour = int(hour) % 24
    except Exception:
        hour = 0
    suffix = "AM" if hour < 12 else "PM"
    display_hour = hour % 12
    if display_hour == 0:
        display_hour = 12
    return f"{display_hour}:00 {suffix}"


def _safe_iso_timestamp(value):
    try:
        return pd.Timestamp(value).isoformat()
    except Exception:
        return str(value)


def _safe_round(value, digits=4):
    try:
        if value is None or pd.isna(value):
            return None
        return round(float(value), digits)
    except Exception:
        return None


def _format_window_label(start, stop):
    try:
        start_ts = pd.Timestamp(start)
        stop_ts = pd.Timestamp(stop)
        return f"{start_ts.strftime('%Y-%m-%d %I:%M %p')} to {stop_ts.strftime('%Y-%m-%d %I:%M %p')}"
    except Exception:
        return f"{start} to {stop}"


def _sleep_window_detail_payload(windows, window_metadata=None):
    metadata = window_metadata or {}
    details = []
    for idx, window in enumerate(windows or [], start=1):
        start = window.get("start")
        stop = window.get("stop")
        duration_hours = None
        try:
            duration_hours = (pd.Timestamp(stop) - pd.Timestamp(start)).total_seconds() / 3600.0
        except Exception:
            duration_hours = window.get("duration_hours")

        detail = {
            "index": idx,
            "date": window.get("night") or window.get("date") or _safe_iso_timestamp(start)[:10],
            "method": window.get("method") or metadata.get("method"),
            "source": window.get("source") or metadata.get("source"),
            "estimated": bool(window.get("estimated", metadata.get("estimated", False))),
            "start": _safe_iso_timestamp(start),
            "stop": _safe_iso_timestamp(stop),
            "duration_hours": _safe_round(duration_hours, 3),
        }

        diagnostics = window.get("diagnostics") or {}
        if diagnostics:
            detail.update({
                "expected_search_start": diagnostics.get("search_start"),
                "expected_search_stop": diagnostics.get("search_stop"),
                "expected_search_range": diagnostics.get("search_range_label"),
                "lowest_sustained_activity_block_start": diagnostics.get("candidate_start"),
                "lowest_sustained_activity_block_stop": diagnostics.get("candidate_stop"),
                "lowest_sustained_activity_block": diagnostics.get("candidate_range_label"),
                "target_window_hours": diagnostics.get("target_hours"),
                "min_window_hours": diagnostics.get("min_hours"),
                "max_window_hours": diagnostics.get("max_hours"),
                "resample_frequency": diagnostics.get("resample_frequency"),
                "rolling_mean_activity": diagnostics.get("rolling_mean_activity"),
                "segment_mean_activity": diagnostics.get("segment_mean_activity"),
                "segment_min_activity": diagnostics.get("segment_min_activity"),
                "segment_max_activity": diagnostics.get("segment_max_activity"),
                "points_in_search_range": diagnostics.get("points_in_search_range"),
                "points_in_detected_window": diagnostics.get("points_in_detected_window"),
            })
        details.append(detail)
    return details


def _summarize_sleep_window_details(details, max_items=4):
    if not details:
        return ""
    lines = []
    for item in details[:max_items]:
        lines.append(
            "Date {date}: sleep/rest window {window}; duration {duration} h; method {method}.".format(
                date=item.get("date") or "unknown",
                window=f"{item.get('start')} to {item.get('stop')}",
                duration=item.get("duration_hours") if item.get("duration_hours") is not None else "not available",
                method=item.get("method") or "not recorded",
            )
        )
    if len(details) > max_items:
        lines.append(f"Additional sleep/rest windows detected: {len(details) - max_items}.")
    return " | ".join(lines)


def _detect_rest_windows_with_pyactigraphy(raw, sleep_window_settings=None):
    settings = sleep_window_settings or {}
    enabled = bool(settings.get("estimateWithoutDiary", True))
    if not enabled:
        return [], {"source": "none", "method": None, "estimated": False, "notes": ["No-diary rest-window estimation disabled."]}

    method_preference = settings.get("method") or "crespo_aot"
    min_hours = float(settings.get("minRestWindowHours", 3) or 3)
    max_hours = float(settings.get("maxRestWindowHours", 14) or 14)
    notes = []

    # Use only the user-selected pyActigraphy AOT method. Do not fall back to
    # a heuristic low-activity window or silently switch to the other AOT method;
    # if the selected method cannot produce usable onset/offset arrays, return a
    # clear note so the UI can show that the sleep-window-dependent metrics are
    # unavailable for this file/configuration.
    method_order = [method_preference]

    for method_name in method_order:
        if method_name == "crespo_aot":
            aot = _call_aot_method(raw, "Crespo_AoT", settings.get("crespoParams", {}))
            label = "pyActigraphy Crespo_AoT"
        elif method_name == "roenneberg_aot":
            aot = _call_aot_method(raw, "Roenneberg_AoT", settings.get("roennebergParams", {}))
            label = "pyActigraphy Roenneberg_AoT"
        else:
            notes.append(f"Unknown rest-window detection method: {method_name}.")
            continue

        if aot is None or not isinstance(aot, (list, tuple)) or len(aot) < 2:
            notes.append(f"{label} did not return usable activity onset/offset arrays.")
            continue

        onsets, offsets = aot[0], aot[1]
        windows = _rest_windows_from_activity_onset_offset(onsets, offsets, min_hours=min_hours, max_hours=max_hours)
        if windows:
            for window in windows:
                window["source"] = "estimated_rest_period"
                window["method"] = label
            return windows, {
                "source": "estimated_rest_period",
                "method": label,
                "estimated": True,
                "notes": notes + [f"Detected {len(windows)} rest window(s) from activity offset/onset times."],
            }
        notes.append(f"{label} ran, but no rest windows passed the duration filters ({min_hours}-{max_hours} h).")

    notes.append(
        "No heuristic fallback sleep window was used. Upload a sleep diary/manual sleep window, "
        "or adjust the selected pyActigraphy Crespo_AoT/Roenneberg_AoT settings if window-dependent sleep metrics are required."
    )
    return [], {"source": "none", "method": None, "estimated": False, "notes": notes}


def _resolve_sleep_windows(raw, sleep_window_settings=None):
    diary_windows = _get_sleep_windows(raw)
    if diary_windows:
        return diary_windows, {
            "source": "sleep_diary",
            "method": "sleep_diary",
            "estimated": False,
            "count": len(diary_windows),
            "notes": [f"Using {len(diary_windows)} diary/user-defined sleep window(s)."],
        }

    detected_windows, metadata = _detect_rest_windows_with_pyactigraphy(raw, sleep_window_settings=sleep_window_settings)
    metadata["count"] = len(detected_windows)
    return detected_windows, metadata


def _window_score_quality(score, windows, minimum_coverage=0.80):
    series = _coerce_score_series(score)
    if series is None or not windows:
        return []
    epoch_minutes = _epoch_minutes(series.index)
    details = []
    for index, window in enumerate(windows, start=1):
        start = pd.Timestamp(window["start"])
        stop = pd.Timestamp(window["stop"])
        duration_minutes = max(0.0, (stop - start).total_seconds() / 60.0)
        # Sleep/rest windows are half-open [start, stop), so adjacent nights do
        # not double-count the stop epoch.
        window_series = series.loc[(series.index >= start) & (series.index < stop)]
        observed = window_series.dropna()
        expected_epochs = max(1, int(round(duration_minutes / max(epoch_minutes, 1e-12))))
        observed_epochs = int(len(observed))
        coverage = min(1.0, observed_epochs / expected_epochs)
        eligible = bool(observed_epochs > 0 and coverage + 1e-12 >= minimum_coverage)
        details.append({
            "index": index,
            "start": start.isoformat(),
            "stop": stop.isoformat(),
            "duration_minutes": duration_minutes,
            "expected_epochs": expected_epochs,
            "observed_epochs": observed_epochs,
            "observed_minutes": observed_epochs * epoch_minutes,
            "coverage_fraction": coverage,
            "minimum_coverage_fraction": minimum_coverage,
            "eligible": eligible,
            "exclusion_reason": None if eligible else (
                f"recorded/scored coverage {coverage:.1%} is below the required {minimum_coverage:.1%}"
            ),
            "score": observed,
        })
    return details


def _score_minutes_in_windows(score, windows, minimum_coverage=0.80):
    series = _coerce_score_series(score)
    if series is None:
        return None, []
    if not windows:
        # TST is window-dependent here. Do not turn the full recording into an
        # implicit fallback sleep window when Crespo/Roenneberg or the diary
        # did not produce a usable interval.
        return None, []
    quality = _window_score_quality(series, windows, minimum_coverage=minimum_coverage)
    usable = [item for item in quality if item["eligible"]]
    if not usable:
        return None, quality
    total_sleep_minutes = sum(
        float((item["score"] > 0).sum()) * _epoch_minutes(series.index)
        for item in usable
    )
    return total_sleep_minutes, quality


def _compute_waso_and_efficiency(score, windows, window_quality=None, minimum_coverage=0.80):
    series = _coerce_score_series(score)
    if series is None or not windows:
        return {
            "waso": None,
            "sleep_efficiency": None,
            "time_in_bed_minutes": None,
            "scheduled_time_in_bed_minutes": None,
            "sleep_window_count": 0,
            "sleep_windows_excluded_for_coverage": 0,
        }

    epoch_minutes = _epoch_minutes(series.index)
    total_sleep_minutes = 0.0
    total_waso_minutes = 0.0
    total_time_in_bed_minutes = 0.0
    total_scheduled_time_in_bed_minutes = 0.0
    usable_windows = 0

    quality = window_quality or _window_score_quality(series, windows, minimum_coverage=minimum_coverage)
    for item in quality:
        if not item["eligible"]:
            continue
        window_series = item["score"]
        if len(window_series) == 0:
            continue

        sleep_mask = window_series > 0
        usable_windows += 1
        total_scheduled_time_in_bed_minutes += float(item["duration_minutes"])
        # Only observed/scored epochs enter the denominator.  Missing epochs
        # are neither sleep nor wake.
        total_time_in_bed_minutes += float(item["observed_minutes"])
        if not bool(sleep_mask.any()):
            # The diary window exists, but the chosen algorithm found no sleep in it.
            continue

        total_sleep_minutes += float(sleep_mask.sum()) * epoch_minutes

        first_sleep_pos = sleep_mask.to_numpy().nonzero()[0][0]
        after_onset = sleep_mask.iloc[first_sleep_pos:]
        total_waso_minutes += float((~after_onset).sum()) * epoch_minutes

    if usable_windows == 0 or total_time_in_bed_minutes <= 0:
        return {
            "waso": None,
            "sleep_efficiency": None,
            "time_in_bed_minutes": None,
            "scheduled_time_in_bed_minutes": None,
            "sleep_window_count": 0,
            "sleep_windows_excluded_for_coverage": len([item for item in quality if not item["eligible"]]),
        }

    return {
        "waso": total_waso_minutes,
        "sleep_efficiency": (total_sleep_minutes / total_time_in_bed_minutes) * 100.0,
        "time_in_bed_minutes": total_time_in_bed_minutes,
        "scheduled_time_in_bed_minutes": total_scheduled_time_in_bed_minutes,
        "sleep_window_count": usable_windows,
        "sleep_windows_excluded_for_coverage": len([item for item in quality if not item["eligible"]]),
    }


def compute_metric(raw, metric_id, params=None):
    params = params or {}

    if metric_id in {"is", "iv", "ism", "ivm", "isp", "ivp", "rap"}:
        if _valid_day_count(raw) < _minimum_valid_days_for_rhythm(raw):
            return None

    if metric_id == "ra":
        return _safe_call(raw.RA, binarize=params.get("binarize", True), threshold=params.get("threshold", 4))

    if metric_id == "is":
        return _safe_call(raw.IS, freq=params.get("freq", "1min"), binarize=params.get("binarize", True), threshold=params.get("threshold", 4))

    if metric_id == "iv":
        return _safe_call(raw.IV, freq=params.get("freq", "1min"), binarize=params.get("binarize", True), threshold=params.get("threshold", 4))

    if metric_id == "ism":
        return _safe_call(raw.ISm, freqs=params.get("freqs") or DEFAULT_MEAN_FREQS, binarize=params.get("binarize", True), threshold=params.get("threshold", 4))

    if metric_id == "ivm":
        return _safe_call(raw.IVm, freqs=params.get("freqs") or DEFAULT_MEAN_FREQS, binarize=params.get("binarize", True), threshold=params.get("threshold", 4))

    if metric_id == "isp":
        return _safe_call(raw.ISp, period=params.get("period", "7D"), freq=params.get("freq", "1min"), binarize=params.get("binarize", True), threshold=params.get("threshold", 4), verbose=params.get("verbose", False))

    if metric_id == "ivp":
        return _safe_call(raw.IVp, period=params.get("period", "7D"), freq=params.get("freq", "1min"), binarize=params.get("binarize", True), threshold=params.get("threshold", 4), verbose=params.get("verbose", False))

    if metric_id == "rap":
        return _safe_call(raw.RAp, period=params.get("period", "7D"), binarize=params.get("binarize", True), threshold=params.get("threshold", 4), verbose=params.get("verbose", False))

    if metric_id == "kra":
        method = getattr(raw, "kRA", None)
        return _safe_call(method, threshold=params.get("threshold", 4), start=params.get("start") or None, period=params.get("period") or None, frac=params.get("frac", 0.3), it=params.get("it", 0), logit=params.get("logit", False), freq=params.get("freq", "1min")) if callable(method) else None

    if metric_id == "kar":
        method = getattr(raw, "kAR", None)
        return _safe_call(method, threshold=params.get("threshold", 4), start=params.get("start") or None, period=params.get("period") or None, frac=params.get("frac", 0.3), it=params.get("it", 0), logit=params.get("logit", False), freq=params.get("freq", "1min")) if callable(method) else None

    return None


def compute_sleep_metrics(raw, selected_metrics=None, algorithm_request=None, sleep_window_settings=None):
    results = {}
    selected_metrics = selected_metrics or []
    algorithm_request = algorithm_request or {}
    algorithm = algorithm_request.get("id", "cole_kripke")
    algorithm_params = {algorithm: algorithm_request.get("params", {})}

    scorer = None
    with diagnostic_stage(
        "sleep.algorithm_score",
        category="sleep",
        details={"algorithm": algorithm, "parameters": algorithm_request.get("params", {})},
    ) as stage:
        scorer = _score_algorithm(raw, algorithm, algorithm_params=algorithm_params)
        scorer = _mask_sleep_score_with_activity(raw, scorer)
        summary = result_summary(scorer)
        update_current_stage(result=summary)
        if scorer is None:
            mark_current_stage(
                "failed" if stage.get("suppressed_errors") else "warning",
                outcome="algorithm_returned_no_score",
            )

    sleep_windows = []
    window_required = any(metric in selected_metrics for metric in ["tst", "waso", "sleep_efficiency"])
    window_metadata = {"source": "none", "method": None, "estimated": False, "count": 0, "notes": []}
    with diagnostic_stage(
        "sleep.window_detection",
        category="sleep_window",
        details={"settings": sleep_window_settings or {}},
    ) as stage:
        sleep_windows, window_metadata = _resolve_sleep_windows(raw, sleep_window_settings=sleep_window_settings)
        update_current_stage(
            window_count=len(sleep_windows),
            source=window_metadata.get("source"),
            method=window_metadata.get("method"),
            estimated=bool(window_metadata.get("estimated")),
            notes=window_metadata.get("notes") or [],
        )
        if not sleep_windows and window_required:
            mark_current_stage(
                "failed" if stage.get("suppressed_errors") else "warning",
                outcome="no_usable_sleep_windows",
            )
        elif not sleep_windows:
            update_current_stage(outcome="sleep_window_not_required_for_selected_metrics")

    minimum_window_coverage = float(getattr(raw, "_ui_min_sleep_window_coverage", 0.80))
    rest_minutes, sleep_window_quality = _score_minutes_in_windows(
        scorer,
        sleep_windows,
        minimum_coverage=minimum_window_coverage,
    )
    sleep_window_summary = _compute_waso_and_efficiency(
        scorer,
        sleep_windows,
        window_quality=sleep_window_quality,
        minimum_coverage=minimum_window_coverage,
    )

    if "sri" in selected_metrics:
        try:
            with diagnostic_stage(
                "metric.sri",
                category="metric",
                details={"metric_id": "sri", "algorithm": algorithm},
            ) as stage:
                algo_key = ALGO_TO_SRI_KEY.get(algorithm)
                if _valid_day_count(raw) < _minimum_valid_days_for_rhythm(raw):
                    results["sri"] = None
                    mark_current_stage(
                        "warning",
                        outcome="insufficient_valid_days",
                        valid_days=_valid_day_count(raw),
                        minimum_valid_days=_minimum_valid_days_for_rhythm(raw),
                    )
                elif algo_key is None or scorer is None:
                    results["sri"] = None
                    mark_current_stage(
                        "warning",
                        outcome="metric_not_supported_for_algorithm_or_raw_type",
                        raw_class=type(raw).__name__,
                    )
                else:
                    results["sri"] = _missing_aware_sri(scorer)
                    update_current_stage(result=result_summary(results["sri"]))
                    if results["sri"] is None:
                        mark_current_stage(
                            "failed" if stage.get("suppressed_errors") else "warning",
                            outcome="metric_returned_no_value",
                        )
        except Exception:
            results["sri"] = None

    if "tst" in selected_metrics:
        try:
            with diagnostic_stage("metric.tst", category="metric", details={"metric_id": "tst", "algorithm": algorithm}):
                results["tst"] = round(rest_minutes, 2) if rest_minutes is not None else None
                update_current_stage(result=result_summary(results["tst"]), sleep_window_count=len(sleep_windows))
                if results["tst"] is None:
                    mark_current_stage("warning", outcome="sleep_score_not_available")
        except Exception:
            results["tst"] = None

    if "waso" in selected_metrics:
        try:
            with diagnostic_stage("metric.waso", category="metric", details={"metric_id": "waso", "algorithm": algorithm}):
                waso = sleep_window_summary.get("waso")
                results["waso"] = round(waso, 2) if waso is not None else None
                update_current_stage(result=result_summary(results["waso"]), sleep_window_count=len(sleep_windows))
                if results["waso"] is None:
                    mark_current_stage("warning", outcome="requires_usable_sleep_window_and_score")
        except Exception:
            results["waso"] = None

    if "sleep_efficiency" in selected_metrics:
        try:
            with diagnostic_stage(
                "metric.sleep_efficiency",
                category="metric",
                details={"metric_id": "sleep_efficiency", "algorithm": algorithm},
            ):
                sleep_efficiency = sleep_window_summary.get("sleep_efficiency")
                results["sleep_efficiency"] = round(sleep_efficiency, 2) if sleep_efficiency is not None else None
                update_current_stage(result=result_summary(results["sleep_efficiency"]), sleep_window_count=len(sleep_windows))
                if results["sleep_efficiency"] is None:
                    mark_current_stage("warning", outcome="requires_usable_sleep_window_and_score")
        except Exception:
            results["sleep_efficiency"] = None

    if any(metric in selected_metrics for metric in ["tst", "waso", "sleep_efficiency"]):
        results["sleep_window_source"] = window_metadata.get("source") or "none"
        results["sleep_window_method"] = window_metadata.get("method") or "none"
        results["sleep_window_count"] = int(sleep_window_summary.get("sleep_window_count") or 0)
        results["sleep_window_detected_count"] = int(window_metadata.get("count") or 0)
        results["time_in_bed_minutes"] = round(sleep_window_summary.get("time_in_bed_minutes"), 2) if sleep_window_summary.get("time_in_bed_minutes") is not None else None
        results["scheduled_time_in_bed_minutes"] = round(sleep_window_summary.get("scheduled_time_in_bed_minutes"), 2) if sleep_window_summary.get("scheduled_time_in_bed_minutes") is not None else None
        results["minimum_sleep_window_coverage"] = round(minimum_window_coverage, 4)
        results["sleep_windows_excluded_for_coverage"] = int(sleep_window_summary.get("sleep_windows_excluded_for_coverage") or 0)
        if sleep_window_quality:
            results["sleep_window_coverage"] = [
                {key: _json_ready_metric_value(value) for key, value in item.items() if key != "score"}
                for item in sleep_window_quality
            ]
        results["sleep_window_estimated"] = bool(window_metadata.get("estimated"))
        details = window_metadata.get("details") or _sleep_window_detail_payload(sleep_windows, window_metadata)
        if details:
            results["sleep_window_details"] = details
            results["sleep_window_details_summary"] = _summarize_sleep_window_details(details) or None
        if window_metadata.get("notes"):
            results["sleep_window_notes"] = " | ".join([str(note) for note in window_metadata.get("notes", [])])

    return results

def _build_metric_requests_from_families(family_requests):
    metric_requests = []
    for family in family_requests or []:
        family_id = family.get("id")
        for metric_id in IMPLEMENTED_FAMILY_METRICS.get(family_id, []):
            metric_requests.append({"id": metric_id, "params": {}})
    return metric_requests


def _run_advanced_family_placeholder(family_id):
    return {
        "status": "planned",
        "family": family_id,
        "message": "{} is selected, but full backend execution is not yet implemented in this UI.".format(family_id),
    }


def _run_basic_pyactigraphy_analysis_single(raw, metric_requests=None, family_requests=None, analysis_scope="metric", algorithm_request=None, sleep_window_settings=None):
    metric_requests = metric_requests or []
    family_requests = family_requests or []
    results = {}

    if analysis_scope == "family":
        metric_requests = _build_metric_requests_from_families(family_requests)
        for family in family_requests:
            family_id = family.get("id")
            if family_id in ADVANCED_FAMILY_IDS:
                results[family_id] = _run_advanced_family_placeholder(family_id)

    rest_and_fragmentation_ids = {"ra", "is", "iv", "ism", "ivm", "isp", "ivp", "rap", "kra", "kar"}
    sleep_ids = {"sri", "tst", "waso", "sleep_efficiency"}

    selected_metric_ids = [item.get("id") for item in metric_requests if item.get("id")]

    for item in metric_requests:
        metric_id = item.get("id")
        params = item.get("params", {}) or {}
        if metric_id not in rest_and_fragmentation_ids:
            continue
        try:
            with diagnostic_stage(
                f"metric.{metric_id}",
                category="metric",
                details={"metric_id": metric_id, "parameters": params, "raw_class": type(raw).__name__},
            ) as stage:
                value = compute_metric(raw, metric_id, params=params)
                resolved = _resolve_series_to_numeric(value)
                results[metric_id] = resolved
                extra_stage_details = {}
                if metric_id == "ra":
                    ra_components = getattr(raw, "_ui_last_ra_components", None)
                    if isinstance(ra_components, dict):
                        extra_stage_details["ra_components"] = ra_components
                update_current_stage(result=result_summary(resolved), **extra_stage_details)
                if resolved is None:
                    mark_current_stage(
                        "failed" if stage.get("suppressed_errors") else "warning",
                        outcome="metric_returned_no_value_or_is_not_supported",
                    )
        except Exception:
            # The diagnostic stage retains the full traceback; continue so other
            # selected metrics can still produce results for this file.
            results[metric_id] = None

    sleep_selected = [metric_id for metric_id in selected_metric_ids if metric_id in sleep_ids]
    if sleep_selected:
        try:
            results.update(
                compute_sleep_metrics(
                    raw,
                    selected_metrics=sleep_selected,
                    algorithm_request=algorithm_request,
                    sleep_window_settings=sleep_window_settings,
                )
            )
        except Exception as exc:
            record_suppressed_exception(
                "compute_sleep_metrics",
                exc,
                note="Unexpected sleep-metric group failure; remaining requested metrics were set to None.",
            )
            for metric_id in sleep_selected:
                results.setdefault(metric_id, None)

    for metric_id in selected_metric_ids:
        if metric_id not in results:
            results[metric_id] = None

    return results

def _parse_daily_time(value, default_time):
    if not value:
        return default_time
    try:
        return pd.to_datetime(str(value)).time()
    except Exception:
        return default_time


def _combine_date_time(day, clock_time):
    return pd.Timestamp(day.date()).replace(
        hour=clock_time.hour,
        minute=clock_time.minute,
        second=getattr(clock_time, "second", 0),
        microsecond=0,
    )


def _generate_repeated_analysis_windows(raw, settings):
    series = _get_activity_series(raw)
    if series is None or len(series) == 0 or not isinstance(series.index, pd.DatetimeIndex):
        return []

    preset = settings.get("intervalPreset") or "manual"
    if preset == "manual":
        return []

    if preset == "weekdays":
        allowed_days = {0, 1, 2, 3, 4}
    elif preset == "weekends":
        allowed_days = {5, 6}
    elif preset == "specific_days":
        allowed_days = {int(day) for day in (settings.get("specificDays") or []) if str(day).strip() != ""}
        if not allowed_days:
            return []
    else:
        return []

    start_time = _parse_daily_time(settings.get("dailyStartTime"), pd.Timestamp("2000-01-01 00:00").time())
    stop_time = _parse_daily_time(settings.get("dailyStopTime"), pd.Timestamp("2000-01-01 00:00").time())
    full_day = not settings.get("dailyStartTime") and not settings.get("dailyStopTime")

    first_day = series.index.min().normalize()
    last_day = series.index.max().normalize()
    days = pd.date_range(first_day, last_day, freq="1D")
    windows = []
    for day in days:
        if int(day.dayofweek) not in allowed_days:
            continue
        if full_day:
            start = day
            stop = day + pd.Timedelta(days=1)
        else:
            start = _combine_date_time(day, start_time)
            stop = _combine_date_time(day, stop_time)
            if stop <= start:
                stop = stop + pd.Timedelta(days=1)
        clipped_start = max(start, series.index.min())
        clipped_stop = min(stop, series.index.max())
        if clipped_stop <= clipped_start:
            continue
        if len(series.loc[clipped_start:clipped_stop].dropna()) == 0:
            continue
        windows.append({
            "index": len(windows) + 1,
            "label": f"{preset.replace('_', ' ').title()} {day.date().isoformat()}",
            "state": "ANALYSIS",
            "start": clipped_start,
            "stop": clipped_stop,
            "source": "repeated_rule",
        })
    return windows


def _normalize_file_id(value):
    if value is None:
        return ""
    text = str(value).strip().lower()
    if not text:
        return ""
    try:
        from pathlib import Path as _Path
        stem = _Path(text).stem
        name = _Path(text).name
        return "|".join(sorted({text, name, stem}))
    except Exception:
        return text


def _identifier_matches_file(identifier, source_filename):
    if not identifier or not source_filename:
        return True
    ident = str(identifier).strip()
    if ident.lower() in {"all", "__all__", "global", "*"}:
        return True
    source_keys = set(_normalize_file_id(source_filename).split("|"))
    ident_keys = set(_normalize_file_id(ident).split("|"))
    return bool(source_keys.intersection(ident_keys))


def _interval_applies_to_file(interval, source_filename=None):
    if not source_filename:
        return True
    file_id = interval.get("fileId") or interval.get("file_id") or interval.get("fileName") or interval.get("filename") or interval.get("source_file")
    return _identifier_matches_file(file_id, source_filename)


def _normalize_analysis_windows(analysis_window_settings=None, raw=None):
    settings = analysis_window_settings or {}
    if settings.get("mode") not in {"selected", "both"}:
        return []

    repeated_windows = _generate_repeated_analysis_windows(raw, settings) if raw is not None else []
    if repeated_windows:
        return repeated_windows

    source_filename = settings.get("sourceFileName") or settings.get("fileId")
    windows = []
    for idx, interval in enumerate(settings.get("manualIntervals", []) or []):
        if not _interval_applies_to_file(interval, source_filename):
            continue
        try:
            start = pd.to_datetime(interval.get("start"))
            stop = pd.to_datetime(interval.get("stop"))
            if pd.isna(start) or pd.isna(stop):
                continue
            if stop <= start:
                stop = stop + pd.Timedelta(days=1)
            if stop <= start:
                continue
            windows.append({
                "index": len(windows) + 1,
                "label": interval.get("label") or "Analysis interval {}".format(len(windows) + 1),
                "state": interval.get("state") or "ANALYSIS",
                "start": start,
                "stop": stop,
                "source": interval.get("source") or "manual_ui",
                "fileId": interval.get("fileId") or interval.get("fileName") or source_filename,
            })
        except Exception:
            continue
    return windows


def _slice_raw_to_window(raw, start, stop):
    window_raw = copy.copy(raw)
    if not hasattr(raw, "data") or raw.data is None:
        raise ValueError("Selected-interval analysis requires raw.data to be available on the loaded recording.")

    window_data = raw.data.loc[start:stop]
    if window_data is None or len(window_data) == 0:
        raise ValueError("No activity samples were found inside this selected interval.")

    try:
        window_raw.data = window_data.copy()
    except Exception:
        # pyActigraphy BaseRaw.data is read-only; scope a shallow copy through
        # its writable start_time/period properties instead.
        window_raw.start_time = window_data.index[0]
        window_raw.period = window_data.index[-1] - window_data.index[0]

    try:
        validity = getattr(raw, "_ui_analysis_valid_mask", None)
        if isinstance(validity, pd.Series):
            scoped_validity = validity.loc[start:stop]
            window_raw._ui_analysis_valid_mask = scoped_validity
            window_raw._ui_valid_day_count = int(
                scoped_validity.loc[scoped_validity].index.normalize().nunique()
            )
    except Exception:
        pass

    # Keep only sleep diary/rest windows that overlap this selected analysis interval.
    try:
        scoped_sleep_windows = []
        for window in getattr(raw, "_ui_sleep_windows", []) or []:
            w_start = pd.to_datetime(window.get("start"))
            w_stop = pd.to_datetime(window.get("stop"))
            if pd.isna(w_start) or pd.isna(w_stop) or w_stop <= start or w_start >= stop:
                continue
            next_window = dict(window)
            next_window["start"] = max(w_start, start).isoformat()
            next_window["stop"] = min(w_stop, stop).isoformat()
            scoped_sleep_windows.append(next_window)
        window_raw._ui_sleep_windows = scoped_sleep_windows
    except Exception:
        pass

    return window_raw


def _average_numeric_window_results(window_results, metric_ids):
    aggregate = {}
    for metric_id in metric_ids:
        values = []
        for item in window_results:
            value = (item.get("results") or {}).get(metric_id)
            if isinstance(value, bool):
                continue
            if isinstance(value, numbers.Number) and math.isfinite(float(value)):
                values.append(float(value))
        if values:
            aggregate[metric_id] = round(sum(values) / len(values), 4)
        else:
            aggregate[metric_id] = None
    return aggregate


def run_basic_pyactigraphy_analysis(raw, metric_requests=None, family_requests=None, analysis_scope="metric", algorithm_request=None, sleep_window_settings=None, analysis_window_settings=None):
    metric_requests = metric_requests or []
    family_requests = family_requests or []
    selected_metric_ids = [item.get("id") for item in metric_requests if item.get("id")]
    analysis_window_mode = (analysis_window_settings or {}).get("mode", "full")
    windows = _normalize_analysis_windows(analysis_window_settings, raw=raw)

    if analysis_window_mode == "both":
        full_results = _run_basic_pyactigraphy_analysis_single(
            raw,
            metric_requests=metric_requests,
            family_requests=family_requests,
            analysis_scope=analysis_scope,
            algorithm_request=algorithm_request,
            sleep_window_settings=sleep_window_settings,
        )
        if not windows:
            full_results["analysis_window_mode"] = "whole_file_plus_intervals"
            full_results["analysis_window_count"] = 0
            full_results["analysis_window_summary"] = "Whole-file metrics were calculated, but no selected intervals matched this recording."
            full_results["analysis_windows"] = []
            return full_results
    elif not windows:
        if analysis_window_mode == "selected":
            empty_result = {metric_id: None for metric_id in selected_metric_ids}
            empty_result["analysis_window_mode"] = "selected_intervals"
            empty_result["analysis_window_count"] = 0
            empty_result["analysis_window_summary"] = "No selected intervals matched this recording. Adjust the selected days/times or switch to whole-file analysis."
            empty_result["analysis_windows"] = []
            return empty_result

        return _run_basic_pyactigraphy_analysis_single(
            raw,
            metric_requests=metric_requests,
            family_requests=family_requests,
            analysis_scope=analysis_scope,
            algorithm_request=algorithm_request,
            sleep_window_settings=sleep_window_settings,
        )

    window_results = []
    for window in windows:
        payload = {
            "index": window["index"],
            "label": window["label"],
            "state": window["state"],
            "start": window["start"].isoformat(),
            "stop": window["stop"].isoformat(),
            "duration_hours": round((window["stop"] - window["start"]).total_seconds() / 3600.0, 4),
            "fileId": window.get("fileId"),
        }
        try:
            scoped_raw = _slice_raw_to_window(raw, window["start"], window["stop"])
            payload["results"] = _run_basic_pyactigraphy_analysis_single(
                scoped_raw,
                metric_requests=metric_requests,
                family_requests=family_requests,
                analysis_scope=analysis_scope,
                algorithm_request=algorithm_request,
                sleep_window_settings=sleep_window_settings,
            )
        except Exception as exc:
            payload["results"] = {}
            payload["error"] = str(exc)
        window_results.append(payload)

    aggregate = _average_numeric_window_results(window_results, selected_metric_ids)
    aggregate["analysis_window_mode"] = "selected_intervals"
    aggregate["analysis_window_count"] = len(window_results)
    aggregate["analysis_window_summary"] = "Top-level numeric metrics are means across selected intervals; open Analysis window details for per-interval values."
    aggregate["analysis_windows"] = window_results

    if analysis_window_mode == "both":
        combined = dict(full_results)
        combined["analysis_window_mode"] = "whole_file_plus_selected_intervals"
        combined["analysis_window_count"] = len(window_results)
        combined["analysis_window_summary"] = "Top-level numeric metrics are from the whole cleaned recording. selected_interval_average stores the mean across the selected intervals; open Analysis window details for per-interval values."
        combined["selected_interval_average"] = {key: value for key, value in aggregate.items() if key not in {"analysis_windows"}}
        combined["analysis_windows"] = window_results
        return combined

    return aggregate



def _index_timezone_info(index):
    tz = getattr(index, "tz", None)
    if tz is None:
        return {
            "timezone_aware": False,
            "timezone": None,
            "note": "Timestamps are timezone-naive. pyActigraphy calculations use the timestamps as stored in the file; confirm the device/export timezone before interpreting clock-time metrics.",
        }
    return {
        "timezone_aware": True,
        "timezone": str(tz),
        "note": "Timestamps include timezone information. Clock-time plots and metrics are shown using the timezone stored on the DateTimeIndex.",
    }


def _mean_daily_wave(series, value_key="mean_activity", max_points=1440):
    if series is None or len(series) == 0:
        return []
    wave = pd.to_numeric(series, errors="coerce").dropna()
    if len(wave) == 0:
        return []
    if not isinstance(wave.index, pd.DatetimeIndex):
        return []
    try:
        if getattr(wave.index, "freq", None) is None:
            inferred = pd.infer_freq(wave.index)
            if inferred is None:
                median_step = pd.Series(wave.index).diff().dropna().median()
                if pd.notna(median_step):
                    inferred = pd.Timedelta(median_step)
            if inferred is not None:
                wave = wave.resample(inferred).mean().dropna()
    except Exception:
        pass
    grouped = wave.groupby(wave.index.strftime("%H:%M")).mean().sort_index()
    if len(grouped) > max_points:
        step = max(1, len(grouped) // max_points)
        grouped = grouped.iloc[::step]
    return [{"time": str(idx), value_key: _safe_float(value)} for idx, value in grouped.items()]


def _sample_full_recording(series, max_points=2000, value_key="activity"):
    if series is None or len(series) == 0:
        return []

    total = len(series)
    step = max(1, total // max_points)
    sampled = series.iloc[::step]

    return [{"timestamp": str(index), value_key: _safe_float(value)} for index, value in sampled.items()]


def build_native_preview(raw, activity_channel="data", resample_freq=None):
    series = _get_activity_series(raw, preferred_channel=activity_channel)
    if series is None:
        raise ValueError("Unable to read the activity signal for preview.")

    preview_series = series.dropna()
    if resample_freq:
        preview_series = preview_series.resample(resample_freq).mean()

    timezone_info = _index_timezone_info(preview_series.index) if len(preview_series) else _index_timezone_info(series.index)
    mean_activity_wave = _mean_daily_wave(preview_series, value_key="mean_activity")
    summary = {
        "rows": int(len(preview_series)),
        "start": str(preview_series.index.min()) if len(preview_series) else None,
        "end": str(preview_series.index.max()) if len(preview_series) else None,
        "activity_channel": activity_channel,
        "resample_freq": resample_freq,
        "preview_mode": "full_recording",
        "device": getattr(raw, "format", None),
        "timezone_aware": timezone_info.get("timezone_aware"),
        "timezone": timezone_info.get("timezone") or "Not provided in file/index",
        "mean_activity_wave_points": len(mean_activity_wave),
    }

    return {
        "preview_available": True,
        "summary": summary,
        "timezone_info": timezone_info,
        "full_recording_preview": _sample_full_recording(preview_series, value_key="activity"),
        "mean_activity_wave": mean_activity_wave,
    }


def _describe_light_scale(raw, channel_name):
    metadata = getattr(raw, "metadata", None) or {}
    channel_scales = metadata.get("light_channels") if isinstance(metadata, dict) else None
    scale = None
    if isinstance(channel_scales, dict) and channel_name:
        scale = channel_scales.get(channel_name) or channel_scales.get(str(channel_name).upper())

    if not scale and channel_name:
        normalized = str(channel_name).strip().upper()
        if normalized in {"LIGHT_LOG", "LOG_LIGHT", "LOG10_LUX", "LIGHT", "WHITE_LIGHT", "AMB_LIGHT"} and metadata.get("direct_geneactiv_reader"):
            scale = "log10(lux + 1)"
        elif "LUX" in normalized:
            scale = "lux"

    if not scale:
        scale = "lux"

    if str(scale).lower() == "log10(lux + 1)":
        return {
            "light_channel": channel_name,
            "light_units": "log10(lux + 1)",
            "light_scale": "log10_lux_plus_one",
            "y_axis_label": "Light intensity, log10(lux + 1)",
            "light_scale_note": "values are log10-transformed from lux to make low and high light exposure easier to view",
        }

    return {
        "light_channel": channel_name,
        "light_units": "lux",
        "light_scale": "lux",
        "y_axis_label": "Light intensity (lux)",
        "light_scale_note": "values are shown in raw lux",
    }


def build_light_preview(raw, resample_freq=None):
    light_series = None
    light_channel_name = None

    # Native pyActigraphy readers like ATR/MTN expose LightRecording plus
    # convenience properties such as white_light / amb_light.
    if hasattr(raw, "white_light") and raw.white_light is not None:
        light_series = raw.white_light
        light_channel_name = "white_light"
    elif hasattr(raw, "amb_light") and raw.amb_light is not None:
        light_series = raw.amb_light
        light_channel_name = "amb_light"
    else:
        light_obj = getattr(raw, "light", None)

        if light_obj is None:
            return {
                "light_preview_available": False,
                "light_preview": [],
                "light_summary": {},
            }

        # If light is already a pandas Series
        if hasattr(light_obj, "dropna"):
            light_series = light_obj

        # If light is a LightRecording, try common channel names
        elif hasattr(light_obj, "get_channel"):
            for channel_name in ["LIGHT", "whitelight", "AMB LIGHT", "LIGHT_LUX", "Lux", "lux"]:
                try:
                    candidate = light_obj.get_channel(channel_name)
                    if candidate is not None:
                        light_series = candidate
                        light_channel_name = channel_name
                        break
                except Exception:
                    pass

            # Fall back to the first available column in the LightRecording dataframe
            if light_series is None and hasattr(light_obj, "data") and light_obj.data is not None:
                try:
                    if len(light_obj.data.columns) > 0:
                        light_series = light_obj.data.iloc[:, 0]
                        light_channel_name = str(light_obj.data.columns[0])
                except Exception:
                    pass

    if light_series is None:
        return {
            "light_preview_available": False,
            "light_preview": [],
            "light_summary": {},
        }

    preview_series = light_series.dropna()
    if len(preview_series) == 0:
        return {
            "light_preview_available": False,
            "light_preview": [],
            "light_summary": {},
        }

    if resample_freq:
        preview_series = preview_series.resample(resample_freq).mean()

    timezone_info = _index_timezone_info(preview_series.index)
    scale_info = _describe_light_scale(raw, light_channel_name)
    summary = {
        "rows": int(len(preview_series)),
        "start": str(preview_series.index.min()) if len(preview_series) else None,
        "end": str(preview_series.index.max()) if len(preview_series) else None,
        "mean_light": _serialize_scalar(preview_series.mean()) if len(preview_series) else None,
        "max_light": _serialize_scalar(preview_series.max()) if len(preview_series) else None,
        "timezone_aware": timezone_info.get("timezone_aware"),
        "timezone": timezone_info.get("timezone") or "Not provided in file/index",
        **scale_info,
    }

    return {
        "light_preview_available": True,
        "timezone_info": timezone_info,
        "light_y_axis_label": scale_info.get("y_axis_label"),
        "light_units": scale_info.get("light_units"),
        "light_scale": scale_info.get("light_scale"),
        "light_preview": _sample_full_recording(preview_series, value_key="light"),
        "light_summary": summary,
    }

def _get_light_channel_series(raw, channel_name):
    light_obj = _get_light_recording(raw)
    if light_obj is None:
        return None

    try:
        series = light_obj.get_channel(channel_name)
    except Exception:
        series = None

    if series is None:
        return None

    if isinstance(series, pd.DataFrame):
        if series.shape[1] == 0:
            return None
        series = series.iloc[:, 0]

    if not isinstance(series, pd.Series):
        return None

    return series.dropna()


def _sample_multichannel_dataframe(df, max_points=1200):
    if df is None or df.empty:
        return []

    df = df.sort_index()

    if len(df) > max_points:
        step = max(1, len(df) // max_points)
        df = df.iloc[::step]

    rows = []
    for idx, row in df.iterrows():
        point = {"timestamp": str(idx)}
        for col in df.columns:
            value = row[col]
            point[col] = None if pd.isna(value) else _serialize_scalar(value)
        rows.append(point)

    return rows


def build_light_rgb_preview(raw, resample_freq="5min"):
    light_obj = _get_light_recording(raw)
    if light_obj is None:
        return {
            "light_preview_available": False,
            "channels": [],
            "rgb_preview": [],
            "rgb_summary": {},
        }

    available_channels = _get_light_channels(raw)

    preferred_channels = [
        "RED LIGHT",
        "GREEN LIGHT",
        "BLUE LIGHT",
        "LIGHT",
        "AMB LIGHT",
        "IR LIGHT",
        "UVA LIGHT",
        "UVB LIGHT",
    ]

    selected_channels = [ch for ch in preferred_channels if ch in available_channels]

    if not selected_channels and available_channels:
        selected_channels = available_channels[:4]

    channel_series = {}
    for channel in selected_channels:
        series = _get_light_channel_series(raw, channel)
        if series is None or len(series) == 0:
            continue

        if resample_freq:
            try:
                series = series.resample(resample_freq).mean()
            except Exception:
                pass

        series = series.dropna()
        if len(series) == 0:
            continue

        channel_series[channel] = series.rename(channel)

    if not channel_series:
        return {
            "light_preview_available": False,
            "channels": available_channels,
            "rgb_preview": [],
            "rgb_summary": {},
        }

    preview_df = pd.concat(channel_series.values(), axis=1)

    channel_scale_info = {channel: _describe_light_scale(raw, channel) for channel in preview_df.columns}
    y_axis_labels = sorted({info.get("y_axis_label") for info in channel_scale_info.values() if info.get("y_axis_label")})
    if len(y_axis_labels) == 1:
        y_axis_label = y_axis_labels[0]
        scale_note = next((info.get("light_scale_note") for info in channel_scale_info.values() if info.get("light_scale_note")), "")
    else:
        y_axis_label = "Light intensity (mixed units/scales)"
        scale_note = "selected channels may use different units; check each channel card for units"

    summary = {
        "rows": int(len(preview_df)),
        "start": str(preview_df.index.min()) if len(preview_df) else None,
        "end": str(preview_df.index.max()) if len(preview_df) else None,
        "channels_used": list(preview_df.columns),
        "y_axis_label": y_axis_label,
        "light_scale_note": scale_note,
        "channel_stats": {},
    }

    for channel in preview_df.columns:
        series = preview_df[channel].dropna()
        scale_info = channel_scale_info.get(channel, {})
        summary["channel_stats"][channel] = {
            "mean": _serialize_scalar(series.mean()) if len(series) else None,
            "max": _serialize_scalar(series.max()) if len(series) else None,
            "min": _serialize_scalar(series.min()) if len(series) else None,
            "units": scale_info.get("light_units"),
            "scale": scale_info.get("light_scale"),
            "y_axis_label": scale_info.get("y_axis_label"),
        }

    return {
        "light_preview_available": True,
        "channels": available_channels,
        "rgb_preview": _sample_multichannel_dataframe(preview_df),
        "rgb_summary": summary,
    }
