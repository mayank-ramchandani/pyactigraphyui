import math
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


def _serialize_scalar(value):
    if value is None:
        return None
    if isinstance(value, (int, float, str, bool)):
        return value
    try:
        return float(value)
    except Exception:
        return str(value)


def _serialize_series(series):
    return {
        "kind": "series",
        "index": [str(i) for i in series.index.tolist()],
        "values": [_serialize_scalar(v) for v in series.tolist()],
        "name": str(series.name) if series.name is not None else None,
    }


def _serialize_dataframe(df):
    if isinstance(df.columns, pd.MultiIndex):
        columns = [" | ".join([str(x) for x in col if x is not None]) for col in df.columns.tolist()]
    else:
        columns = [str(c) for c in df.columns.tolist()]

    rows = []
    for idx, row in df.iterrows():
        rows.append(
            {
                "index": str(idx),
                "values": [_serialize_scalar(v) for v in row.tolist()],
            }
        )

    return {
        "kind": "dataframe",
        "columns": columns,
        "rows": rows,
    }


def _select_channel_from_result(result, channel):
    if channel is None:
        return result

    if isinstance(result, pd.Series):
        if channel in result.index:
            return result.loc[channel]
        return result

    if isinstance(result, pd.DataFrame):
        if isinstance(result.columns, pd.MultiIndex):
            if channel in result.columns.get_level_values(0):
                return result[channel]
        elif channel in result.columns:
            return result[channel]
        return result

    return result


def run_basic_pylight_analysis(
    raw,
    metric_id,
    channel=None,
    threshold_lux=None,
    start_time=None,
    stop_time=None,
    bins="24h",
    agg="mean",
    agg_funcs=None,
    oformat="minute",
):
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
        result = light_obj.light_exposure_level(
            threshold=threshold,
            start_time=start_time or None,
            stop_time=stop_time or None,
            agg=agg or "mean",
        )
        result = _select_channel_from_result(result, channel)

    elif metric_id == "summary_stats":
        if not agg_funcs:
            agg_funcs = ["mean", "median", "sum", "std", "min", "max"]

        result = light_obj.summary_statistics_per_time_bin(
            bins=bins or "24h",
            agg_func=agg_funcs,
        )
        result = _select_channel_from_result(result, channel)

    elif metric_id == "tat":
        result = light_obj.TAT(
            threshold=threshold,
            start_time=start_time or None,
            stop_time=stop_time or None,
            oformat=oformat or "minute",
        )
        result = _select_channel_from_result(result, channel)

    else:
        raise ValueError("Unsupported light metric '{}'.".format(metric_id))

    if isinstance(result, pd.DataFrame):
        payload = _serialize_dataframe(result)
    elif isinstance(result, pd.Series):
        payload = _serialize_series(result)
    else:
        payload = {
            "kind": "scalar",
            "value": _serialize_scalar(result),
        }

    return {
        "metric_id": metric_id,
        "channel": channel,
        "available_channels": channels,
        "threshold_lux": _serialize_scalar(threshold_lux),
        "threshold_log10": _serialize_scalar(threshold),
        "result": payload,
    }


def get_basic_light_channels(raw):
    channels = _get_light_channels(raw)
    return {
        "channels": channels,
        "default_channel": _pick_default_light_channel(channels),
    }

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


def _score_algorithm(raw, algorithm, algorithm_params=None):
    algorithm_params = algorithm_params or {}
    params = algorithm_params.get(algorithm, {}) if isinstance(algorithm_params, dict) else {}

    if algorithm == "cole_kripke":
        return _safe_call(raw.CK)
    if algorithm == "sadeh":
        return _safe_call(raw.Sadeh)
    if algorithm == "scripps":
        return _safe_call(raw.Scripps)
    if algorithm == "oakley":
        threshold_mode = params.get("thresholdMode", ["auto"])
        if isinstance(threshold_mode, str):
            threshold_mode = [threshold_mode]
        mode = threshold_mode[0] if threshold_mode else "auto"
        threshold = "automatic" if mode == "auto" else params.get("manualThreshold", 40)
        return _safe_call(raw.Oakley, threshold=threshold)
    if algorithm == "crespo":
        alpha_mode = params.get("alphaMode", "default")
        if alpha_mode == "manual":
            alpha = "{}h".format(params.get("alpha", 8))
            return _safe_call(raw.Crespo, alpha=alpha)
        if alpha_mode == "auto":
            return _safe_call(raw.Crespo, estimate_zeta=True)
        return _safe_call(raw.Crespo)
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
        return _safe_call(raw.Roenneberg, threshold=factor)
    return None


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


def compute_sleep_metrics(raw, selected_metrics=None, algorithm_request=None):
    results = {}
    selected_metrics = selected_metrics or []
    algorithm_request = algorithm_request or {}
    algorithm = algorithm_request.get("id", "cole_kripke")
    algorithm_params = {algorithm: algorithm_request.get("params", {})}

    scorer = _score_algorithm(raw, algorithm, algorithm_params=algorithm_params)

    if "sri" in selected_metrics:
        algo_key = ALGO_TO_SRI_KEY.get(algorithm)
        if algo_key is None:
            results["sri"] = None
        else:
            results["sri"] = _safe_call(raw.SleepRegularityIndex, algo=algo_key)

    if scorer is not None and hasattr(scorer, "sum"):
        if "tst" in selected_metrics:
            results["tst"] = _resolve_series_to_numeric(_safe_call(scorer.sum))
        if "waso" in selected_metrics:
            results["waso"] = None
        if "sleep_efficiency" in selected_metrics:
            results["sleep_efficiency"] = None
    else:
        for metric_id in ["tst", "waso", "sleep_efficiency"]:
            if metric_id in selected_metrics:
                results[metric_id] = None

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


def run_basic_pyactigraphy_analysis(raw, metric_requests=None, family_requests=None, analysis_scope="metric", algorithm_request=None):
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
        results.update(compute_sleep_metrics(raw, selected_metrics=sleep_selected, algorithm_request=algorithm_request))

    for metric_id in selected_metric_ids:
        if metric_id not in results:
            results[metric_id] = None

    return results


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

    summary = {
        "rows": int(len(preview_series)),
        "start": str(preview_series.index.min()) if len(preview_series) else None,
        "end": str(preview_series.index.max()) if len(preview_series) else None,
        "activity_channel": activity_channel,
        "resample_freq": resample_freq,
        "preview_mode": "full_recording",
        "device": getattr(raw, "format", None),
    }

    return {
        "preview_available": True,
        "summary": summary,
        "full_recording_preview": _sample_full_recording(preview_series, value_key="activity"),
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

    summary = {
        "rows": int(len(preview_series)),
        "start": str(preview_series.index.min()) if len(preview_series) else None,
        "end": str(preview_series.index.max()) if len(preview_series) else None,
        "mean_light": float(preview_series.mean()) if len(preview_series) else None,
        "max_light": float(preview_series.max()) if len(preview_series) else None,
    }

    return {
        "light_preview_available": True,
        "light_preview": _sample_full_recording(preview_series, value_key="light"),
        "light_summary": summary,
    }