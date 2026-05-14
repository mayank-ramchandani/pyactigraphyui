import math
import numbers
import pandas as pd


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

    if metric_id == "exposure_level":
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
    return {"metric_id": metric_id, "channel": channel, "available_channels": channels, "threshold_lux": _serialize_scalar(threshold_lux), "threshold_log10": _serialize_scalar(threshold), "result": payload}


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
        return float(value)
    except Exception:
        return value


def _safe_call(callable_obj, *args, **kwargs):
    try:
        return callable_obj(*args, **kwargs)
    except Exception:
        return None


def _resolve_series_to_numeric(value):
    if value is None:
        return None
    try:
        return float(value)
    except Exception:
        return value


def _call_raw_method(raw, method_name, *args, **kwargs):
    method = getattr(raw, method_name, None)
    if method is None or not callable(method):
        return None
    return _safe_call(method, *args, **kwargs)


def _score_algorithm(raw, algorithm, algorithm_params=None):
    algorithm_params = algorithm_params or {}
    params = algorithm_params.get(algorithm, {}) if isinstance(algorithm_params, dict) else {}

    if algorithm == "cole_kripke":
        return _call_raw_method(raw, "CK")
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
        alpha_mode = params.get("alphaMode", "default")
        if alpha_mode == "manual":
            alpha = "{}h".format(params.get("alpha", 8))
            return _call_raw_method(raw, "Crespo", alpha=alpha)
        if alpha_mode == "auto":
            return _call_raw_method(raw, "Crespo", estimate_zeta=True)
        return _call_raw_method(raw, "Crespo")
    if algorithm == "roenneberg":
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
        return _call_raw_method(raw, "Roenneberg", threshold=factor)
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
        if score.shape[1] == 1:
            score = score.iloc[:, 0]
        else:
            numeric_cols = score.select_dtypes(include="number").columns
            if len(numeric_cols) == 0:
                return None
            score = score[numeric_cols[0]]
    if not isinstance(score, pd.Series):
        try:
            score = pd.Series(score)
        except Exception:
            return None
    numeric = pd.to_numeric(score, errors="coerce").dropna()
    return numeric if len(numeric) else None


def _score_rest_minutes(score):
    series = _coerce_score_series(score)
    if series is None:
        return None
    return float((series > 0).sum()) * _epoch_minutes(series.index)


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
            for key in ["trend_period", "min_trend_period", "threshold", "min_seed_period", "max_test_period", "min_period", "verbose"]:
                if key in params and params[key] not in (None, ""):
                    kwargs[key] = params[key]
            return method(**kwargs)
        return method()
    except Exception:
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


def _detect_rest_windows_with_pyactigraphy(raw, sleep_window_settings=None):
    settings = sleep_window_settings or {}
    enabled = bool(settings.get("estimateWithoutDiary", True))
    if not enabled:
        return [], {"source": "none", "method": None, "estimated": False, "notes": ["No-diary rest-window estimation disabled."]}

    method_preference = settings.get("method") or "crespo_aot"
    min_hours = float(settings.get("minRestWindowHours", 3) or 3)
    max_hours = float(settings.get("maxRestWindowHours", 14) or 14)
    notes = []

    method_order = [method_preference]
    for fallback in ["crespo_aot", "roenneberg_aot"]:
        if fallback not in method_order:
            method_order.append(fallback)

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

        if not aot or not isinstance(aot, (list, tuple)) or len(aot) < 2:
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


def _score_minutes_in_windows(score, windows):
    series = _coerce_score_series(score)
    if series is None:
        return None
    if not windows:
        return _score_rest_minutes(series)

    epoch_minutes = _epoch_minutes(series.index)
    total_sleep_minutes = 0.0
    usable_windows = 0
    for window in windows:
        window_series = series.loc[window["start"]:window["stop"]].dropna()
        if len(window_series) == 0:
            continue
        usable_windows += 1
        total_sleep_minutes += float((window_series > 0).sum()) * epoch_minutes
    if usable_windows == 0:
        return None
    return total_sleep_minutes


def _compute_waso_and_efficiency(score, windows):
    series = _coerce_score_series(score)
    if series is None or not windows:
        return {
            "waso": None,
            "sleep_efficiency": None,
            "time_in_bed_minutes": None,
            "sleep_window_count": 0,
        }

    epoch_minutes = _epoch_minutes(series.index)
    total_sleep_minutes = 0.0
    total_waso_minutes = 0.0
    total_time_in_bed_minutes = 0.0
    usable_windows = 0

    for window in windows:
        start = window["start"]
        stop = window["stop"]
        if stop <= start:
            continue
        window_series = series.loc[start:stop].dropna()
        if len(window_series) == 0:
            continue

        sleep_mask = window_series > 0
        if not bool(sleep_mask.any()):
            # The diary window exists, but the chosen algorithm found no sleep in it.
            usable_windows += 1
            total_time_in_bed_minutes += (stop - start).total_seconds() / 60.0
            continue

        usable_windows += 1
        total_time_in_bed_minutes += (stop - start).total_seconds() / 60.0
        total_sleep_minutes += float(sleep_mask.sum()) * epoch_minutes

        first_sleep_pos = sleep_mask.to_numpy().nonzero()[0][0]
        after_onset = sleep_mask.iloc[first_sleep_pos:]
        total_waso_minutes += float((~after_onset).sum()) * epoch_minutes

    if usable_windows == 0 or total_time_in_bed_minutes <= 0:
        return {
            "waso": None,
            "sleep_efficiency": None,
            "time_in_bed_minutes": None,
            "sleep_window_count": 0,
        }

    return {
        "waso": total_waso_minutes,
        "sleep_efficiency": (total_sleep_minutes / total_time_in_bed_minutes) * 100.0,
        "time_in_bed_minutes": total_time_in_bed_minutes,
        "sleep_window_count": usable_windows,
    }


def compute_metric(raw, metric_id, params=None):
    params = params or {}

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
        return _safe_call(raw.kRA, threshold=params.get("threshold", 4), start=params.get("start") or None, period=params.get("period") or None, frac=params.get("frac", 0.3), it=params.get("it", 0), logit=params.get("logit", False), freq=params.get("freq", "1min"))

    if metric_id == "kar":
        return _safe_call(raw.kAR, threshold=params.get("threshold", 4), start=params.get("start") or None, period=params.get("period") or None, frac=params.get("frac", 0.3), it=params.get("it", 0), logit=params.get("logit", False), freq=params.get("freq", "1min"))

    return None


def compute_sleep_metrics(raw, selected_metrics=None, algorithm_request=None, sleep_window_settings=None):
    results = {}
    selected_metrics = selected_metrics or []
    algorithm_request = algorithm_request or {}
    algorithm = algorithm_request.get("id", "cole_kripke")
    algorithm_params = {algorithm: algorithm_request.get("params", {})}

    scorer = _score_algorithm(raw, algorithm, algorithm_params=algorithm_params)
    sleep_windows, window_metadata = _resolve_sleep_windows(raw, sleep_window_settings=sleep_window_settings)
    rest_minutes = _score_minutes_in_windows(scorer, sleep_windows)
    sleep_window_summary = _compute_waso_and_efficiency(scorer, sleep_windows)

    if "sri" in selected_metrics:
        algo_key = ALGO_TO_SRI_KEY.get(algorithm)
        if algo_key is None:
            results["sri"] = None
        else:
            results["sri"] = _safe_call(raw.SleepRegularityIndex, algo=algo_key)

    if "tst" in selected_metrics:
        results["tst"] = round(rest_minutes, 2) if rest_minutes is not None else None

    if "waso" in selected_metrics:
        waso = sleep_window_summary.get("waso")
        results["waso"] = round(waso, 2) if waso is not None else None

    if "sleep_efficiency" in selected_metrics:
        sleep_efficiency = sleep_window_summary.get("sleep_efficiency")
        results["sleep_efficiency"] = round(sleep_efficiency, 2) if sleep_efficiency is not None else None

    if any(metric in selected_metrics for metric in ["tst", "waso", "sleep_efficiency"]):
        results["sleep_window_source"] = window_metadata.get("source") or "none"
        results["sleep_window_method"] = window_metadata.get("method") or "none"
        results["sleep_window_count"] = int(window_metadata.get("count") or sleep_window_summary.get("sleep_window_count") or 0)
        results["time_in_bed_minutes"] = round(sleep_window_summary.get("time_in_bed_minutes"), 2) if sleep_window_summary.get("time_in_bed_minutes") is not None else None
        results["sleep_window_estimated"] = bool(window_metadata.get("estimated"))
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


def run_basic_pyactigraphy_analysis(raw, metric_requests=None, family_requests=None, analysis_scope="metric", algorithm_request=None, sleep_window_settings=None):
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
        if metric_id in rest_and_fragmentation_ids:
            value = compute_metric(raw, metric_id, params=params)
            results[metric_id] = _resolve_series_to_numeric(value)

    sleep_selected = [metric_id for metric_id in selected_metric_ids if metric_id in sleep_ids]
    if sleep_selected:
        results.update(compute_sleep_metrics(raw, selected_metrics=sleep_selected, algorithm_request=algorithm_request, sleep_window_settings=sleep_window_settings))

    for metric_id in selected_metric_ids:
        if metric_id not in results:
            results[metric_id] = None

    return results



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
    series = getattr(raw, "data", None)
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


def build_light_preview(raw, resample_freq=None):
    light_series = None

    # Native pyActigraphy readers like ATR/MTN expose LightRecording plus
    # convenience properties such as white_light / amb_light.
    if hasattr(raw, "white_light") and raw.white_light is not None:
        light_series = raw.white_light
    elif hasattr(raw, "amb_light") and raw.amb_light is not None:
        light_series = raw.amb_light
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
            for channel_name in ["LIGHT", "whitelight", "AMB LIGHT"]:
                try:
                    candidate = light_obj.get_channel(channel_name)
                    if candidate is not None:
                        light_series = candidate
                        break
                except Exception:
                    pass

            # Fall back to the first available column in the LightRecording dataframe
            if light_series is None and hasattr(light_obj, "data") and light_obj.data is not None:
                try:
                    if len(light_obj.data.columns) > 0:
                        light_series = light_obj.data.iloc[:, 0]
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
    summary = {
        "rows": int(len(preview_series)),
        "start": str(preview_series.index.min()) if len(preview_series) else None,
        "end": str(preview_series.index.max()) if len(preview_series) else None,
        "mean_light": _serialize_scalar(preview_series.mean()) if len(preview_series) else None,
        "max_light": _serialize_scalar(preview_series.max()) if len(preview_series) else None,
        "timezone_aware": timezone_info.get("timezone_aware"),
        "timezone": timezone_info.get("timezone") or "Not provided in file/index",
    }

    return {
        "light_preview_available": True,
        "timezone_info": timezone_info,
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

    summary = {
        "rows": int(len(preview_df)),
        "start": str(preview_df.index.min()) if len(preview_df) else None,
        "end": str(preview_df.index.max()) if len(preview_df) else None,
        "channels_used": list(preview_df.columns),
        "channel_stats": {},
    }

    for channel in preview_df.columns:
        series = preview_df[channel].dropna()
        summary["channel_stats"][channel] = {
            "mean": _serialize_scalar(series.mean()) if len(series) else None,
            "max": _serialize_scalar(series.max()) if len(series) else None,
            "min": _serialize_scalar(series.min()) if len(series) else None,
        }

    return {
        "light_preview_available": True,
        "channels": available_channels,
        "rgb_preview": _sample_multichannel_dataframe(preview_df),
        "rgb_summary": summary,
    }