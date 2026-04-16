import pandas as pd

DEFAULT_MEAN_FREQS = [
    "1min",
    "2min",
    "3min",
    "4min",
    "5min",
    "6min",
    "8min",
    "9min",
    "10min",
    "12min",
    "15min",
    "16min",
    "18min",
    "20min",
    "24min",
    "30min",
    "32min",
    "36min",
    "40min",
    "45min",
    "48min",
    "60min",
]

ALGO_TO_SRI_KEY = {
    "cole_kripke": "CK",
    "sadeh": "Sadeh",
    "oakley": "Oakley",
    "scripps": "Scripps",
    "crespo": "Crespo",
    "roenneberg": "Roenneberg",
}


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


def attach_sleep_diary(raw, diary_path: str):
    raw.read_sleep_diary(diary_path, header_size=2)
    return raw


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
            alpha = f"{params.get('alpha', 8)}h"
            return _safe_call(raw.Crespo, alpha=alpha)
        if alpha_mode == "auto":
            return _safe_call(raw.Crespo, estimate_zeta=True)
        return _safe_call(raw.Crespo)
    if algorithm == "roenneberg":
        factors = params.get("thresholdFactors") or params.get("thresholdFactorsText") or [0.15]
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


def compute_metric(raw, metric_id, *, resample_freq="1min", binarize=True, threshold=4, period="7D", mean_resample_freqs=None, fragmentation_start=None, fragmentation_period=None, lowess_frac=0.3, lowess_it=0, logit_transform=False):
    mean_resample_freqs = mean_resample_freqs or DEFAULT_MEAN_FREQS

    if metric_id == "ra":
        return _safe_call(raw.RA, binarize=binarize, threshold=threshold)
    if metric_id == "is":
        return _safe_call(raw.IS, freq=resample_freq, binarize=binarize, threshold=threshold)
    if metric_id == "iv":
        return _safe_call(raw.IV, freq=resample_freq, binarize=binarize, threshold=threshold)
    if metric_id == "ism":
        return _safe_call(raw.ISm, freqs=mean_resample_freqs, binarize=binarize, threshold=threshold)
    if metric_id == "ivm":
        return _safe_call(raw.IVm, freqs=mean_resample_freqs, binarize=binarize, threshold=threshold)
    if metric_id == "isp":
        return _safe_call(raw.ISp, period=period, freq=resample_freq, binarize=binarize, threshold=threshold, verbose=False)
    if metric_id == "ivp":
        return _safe_call(raw.IVp, period=period, freq=resample_freq, binarize=binarize, threshold=threshold, verbose=False)
    if metric_id == "rap":
        return _safe_call(raw.RAp, period=period, binarize=binarize, threshold=threshold, verbose=False)
    if metric_id == "kra":
        return _safe_call(
            raw.kRA,
            threshold=threshold,
            start=fragmentation_start or None,
            period=fragmentation_period or None,
            frac=lowess_frac,
            it=lowess_it,
            logit=logit_transform,
            freq=resample_freq,
        )
    if metric_id == "kar":
        return _safe_call(
            raw.kAR,
            threshold=threshold,
            start=fragmentation_start or None,
            period=fragmentation_period or None,
            frac=lowess_frac,
            it=lowess_it,
            logit=logit_transform,
            freq=resample_freq,
        )
    return None


def compute_sleep_metrics(raw, selected_metrics=None, algorithm="cole_kripke", algorithm_params=None):
    results = {}
    selected_metrics = selected_metrics or []

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


def run_basic_pyactigraphy_analysis(
    raw,
    selected_metrics,
    selected_algorithm="cole_kripke",
    binarize=True,
    threshold=4,
    advanced_metric_params=None,
    algorithm_params=None,
):
    advanced_metric_params = advanced_metric_params or {}
    results = {}

    rest_and_fragmentation_ids = {"ra", "is", "iv", "ism", "ivm", "isp", "ivp", "rap", "kra", "kar"}
    sleep_ids = {"sri", "tst", "waso", "sleep_efficiency"}

    for metric_id in selected_metrics:
        if metric_id in rest_and_fragmentation_ids:
            value = compute_metric(
                raw,
                metric_id,
                resample_freq=advanced_metric_params.get("resampleFreq") or advanced_metric_params.get("resample_freq") or advanced_metric_params.get("freq") or "1min",
                binarize=binarize,
                threshold=threshold,
                period=advanced_metric_params.get("period", "7D"),
                mean_resample_freqs=advanced_metric_params.get("meanResampleFreqs") or DEFAULT_MEAN_FREQS,
                fragmentation_start=advanced_metric_params.get("fragmentationStart"),
                fragmentation_period=advanced_metric_params.get("fragmentationPeriod"),
                lowess_frac=advanced_metric_params.get("lowessFrac", 0.3),
                lowess_it=advanced_metric_params.get("lowessIt", 0),
                logit_transform=advanced_metric_params.get("logitTransform", False),
            )
            results[metric_id] = _resolve_series_to_numeric(value)

    sleep_selected = [metric for metric in selected_metrics if metric in sleep_ids]
    if sleep_selected:
        results.update(
            compute_sleep_metrics(
                raw,
                selected_metrics=sleep_selected,
                algorithm=selected_algorithm,
                algorithm_params=algorithm_params,
            )
        )

    for metric_id in selected_metrics:
        if metric_id not in results:
            results[metric_id] = None

    return results


def run_basic_csv_analysis(
    df,
    selected_metrics=None,
    activity_channel="VM",
    resample_freq="1min",
    analysis_mode="standard",
    advanced_metric_params=None,
):
    results = {}
    selected_metrics = selected_metrics or []

    if activity_channel not in df.columns:
        raise ValueError(f"Selected activity channel '{activity_channel}' not found in CSV.")

    work = df.copy()
    work["Timestamp"] = pd.to_datetime(work["Timestamp"], errors="coerce")
    work = work.dropna(subset=["Timestamp"]).sort_values("Timestamp")
    work = work.set_index("Timestamp")

    if resample_freq:
        work = work.resample(resample_freq).mean(numeric_only=True)

    work["day_type"] = work.index.dayofweek.map(lambda x: "weekend" if x >= 5 else "weekday")
    work["date"] = work.index.date

    daily = (
        work.groupby(["date", "day_type"], as_index=False)[activity_channel]
        .mean()
        .rename(columns={activity_channel: "activity_mean"})
    )

    results["days_detected"] = int(daily["date"].nunique())
    results["mean_weekday_activity"] = (
        float(daily.loc[daily["day_type"] == "weekday", "activity_mean"].mean())
        if not daily.loc[daily["day_type"] == "weekday"].empty
        else None
    )
    results["mean_weekend_activity"] = (
        float(daily.loc[daily["day_type"] == "weekend", "activity_mean"].mean())
        if not daily.loc[daily["day_type"] == "weekend"].empty
        else None
    )

    unsupported_for_csv = ["ra", "is", "iv", "ism", "ivm", "isp", "ivp", "rap", "kra", "kar", "sri", "tst", "waso", "sleep_efficiency"]
    for metric_id in selected_metrics:
        if metric_id in unsupported_for_csv:
            results[metric_id] = None

    return results


def _sample_full_recording(series, max_points=2000):
    if series is None or len(series) == 0:
        return []

    total = len(series)
    step = max(1, total // max_points)
    sampled = series.iloc[::step]

    return [
        {
            "timestamp": str(index),
            "activity": _safe_float(value),
        }
        for index, value in sampled.items()
    ]


def build_basic_preview(
    df,
    preview_day_mode="all",
    activity_channel="VM",
    resample_freq="1min",
):
    if activity_channel not in df.columns:
        raise ValueError(f"Selected activity channel '{activity_channel}' not found in CSV.")

    work = df.copy()
    work["Timestamp"] = pd.to_datetime(work["Timestamp"], errors="coerce")
    work = work.dropna(subset=["Timestamp"]).sort_values("Timestamp")
    work = work.set_index("Timestamp")

    if resample_freq:
        work = work.resample(resample_freq).mean(numeric_only=True)

    full_series = work[activity_channel].dropna()

    summary = {
        "rows": int(len(full_series)),
        "start": str(full_series.index.min()) if len(full_series) else None,
        "end": str(full_series.index.max()) if len(full_series) else None,
        "activity_channel": activity_channel,
        "resample_freq": resample_freq,
        "preview_mode": "full_recording",
    }

    return {
        "preview_available": True,
        "summary": summary,
        "full_recording_preview": _sample_full_recording(full_series),
    }


def build_native_preview(raw, activity_channel="data", resample_freq=None):
    series = getattr(raw, "data", None)
    if series is None:
        raise ValueError("Unable to read the native activity signal for preview.")

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
        "full_recording_preview": _sample_full_recording(preview_series),
    }
