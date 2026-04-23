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
    light_series = getattr(raw, "light", None)
    if light_series is None:
        return {"light_preview_available": False, "light_preview": []}

    preview_series = light_series.dropna()
    if len(preview_series) == 0:
        return {"light_preview_available": False, "light_preview": []}

    if resample_freq:
        preview_series = preview_series.resample(resample_freq).mean()

    return {
        "light_preview_available": True,
        "light_preview": _sample_full_recording(preview_series, value_key="light"),
    }