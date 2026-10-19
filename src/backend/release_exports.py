"""Research-oriented daily and aggregated outputs from ActiLab's *actual* QC mask.

Unlike a GGIR output translator this module never fabricates GGIR-only sleep,
wear, or physical-activity intensity metrics. It only exports quantities that
ActiLab computed, with explicit level, missingness and provenance semantics.
"""
from __future__ import annotations

from datetime import datetime, timezone
from importlib import metadata as distribution_metadata
from typing import Any

import numpy as np
import pandas as pd


def _simple_value(value):
    if isinstance(value, (str, int, bool)) or value is None:
        return value
    if isinstance(value, (float, np.number)):
        return round(float(value), 6) if np.isfinite(value) else None
    return None


def _scalars(results: dict) -> dict:
    """Only flatten true recording-level scalar results; never average windows."""
    values = {}
    for key, value in (results or {}).items():
        if key in {"analysis_windows", "selected_interval_average", "sleep_window_details", "sleep_window_coverage"}:
            continue
        if isinstance(value, dict):
            if value.get("kind") == "scalar":
                value = value.get("value")
            else:
                continue
        scalar = _simple_value(value)
        if scalar is not None:
            values[key] = scalar
    return values


def build_release_tables(analysis_raw: Any, results: dict, data_quality: dict, *, source_name: str, analysis_config: dict | None = None) -> dict:
    """Make one row per quality window and one row per participant/recording.

    Uses cleaned epoch mask rather than unmasked/entire-recording source data.
    In selected-interval mode QC rows are labelled as QC coverage, not as
    selected-interval per-day derived metrics; interval metrics remain in
    the standard results JSON.
    """
    qc_rows = (data_quality or {}).get("daily_qc") or []
    series = getattr(analysis_raw, "_ui_source_activity_series", None)
    valid = getattr(analysis_raw, "_ui_analysis_valid_mask", None)
    if isinstance(series, pd.Series) and isinstance(valid, pd.Series):
        valid = valid.reindex(series.index, fill_value=False).astype(bool)
        cleaned = pd.to_numeric(series, errors="coerce").where(valid)
    else:
        cleaned = pd.Series(dtype=float)
    mode = (analysis_config or {}).get("analysisWindowSettings", {}).get("mode", "full")
    daily = []
    for row in qc_rows:
        start, end = pd.Timestamp(row["window_start"]), pd.Timestamp(row["window_stop"])
        # QC period is half-open in the source implementation.
        part = cleaned.loc[(cleaned.index >= start) & (cleaned.index < end)].dropna()
        entry = {"source_file": source_name, "output_level": "quality_window", **row}
        entry["activity_mean_valid_epochs"] = _simple_value(float(part.mean())) if len(part) else None
        entry["activity_median_valid_epochs"] = _simple_value(float(part.median())) if len(part) else None
        entry["activity_valid_epochs"] = int(len(part))
        if (data_quality or {}).get("valid_day_window_mode") == "calendar_day":
            # Only attach windows whose *start date* is this calendar day.
            # Do not average across nights or assume SPT and QC day align.
            nights = [night for night in (results or {}).get("sleep_window_nights", [])
                      if isinstance(night, dict) and night.get("sleep_night_start_date") == row.get("date")]
            if nights:
                valid_nights = [night for night in nights if night.get("sleep_window_valid")]
                entry["sleep_window_count_starting_today"] = len(nights)
                entry["sleep_nights_valid"] = len(valid_nights)
                if valid_nights:
                    entry["sleep_tst_minutes"] = _simple_value(sum(n.get("sleep_tst_minutes") or 0 for n in valid_nights))
                    available_waso = [n.get("sleep_waso_minutes") for n in valid_nights if n.get("sleep_waso_minutes") is not None]
                    entry["sleep_waso_minutes"] = _simple_value(sum(available_waso)) if available_waso else None
                    observed = sum(n.get("sleep_observed_minutes") or 0 for n in valid_nights)
                    entry["sleep_efficiency_percent"] = _simple_value(100 * entry["sleep_tst_minutes"] / observed) if observed else None
                entry["sleep_night_assignment_note"] = "Sleep windows grouped by start date, not by midnight-to-midnight overlap"
        daily.append(entry)

    all_valid = cleaned.dropna()
    aggregated = {
        "source_file": source_name,
        "output_level": "recording",
        "recording_start": (data_quality or {}).get("recording_start"),
        "recording_end": (data_quality or {}).get("recording_end"),
        "epoch_seconds": (data_quality or {}).get("epoch_seconds"),
        "quality_window_mode": (data_quality or {}).get("valid_day_window_mode"),
        "n_quality_windows": len(qc_rows),
        "n_valid_quality_windows": sum(bool(row.get("valid_day")) for row in qc_rows),
        "activity_mean_valid_epochs": _simple_value(float(all_valid.mean())) if len(all_valid) else None,
        "activity_median_valid_epochs": _simple_value(float(all_valid.median())) if len(all_valid) else None,
        "activity_valid_epochs": int(len(all_valid)),
        **_scalars(results),
    }
    return {
        "schema_version": "actilab-release-tables-1.0",
        "daily_rows": daily,
        "aggregated_rows": [aggregated],
        "daily_scope": "QC windows over whole cleaned recording; interval-specific results are in standard JSON" if mode in {"selected", "both"} else "whole cleaned recording",
        "aggregation_notes": "Recording-level rhythm/sleep measures are computed by the analysis engine, not means of daily QC rows. Valid epoch activity mean is duration-weighted for regular epochs.",
    }


def _version(name: str):
    try:
        return distribution_metadata.version(name)
    except (distribution_metadata.PackageNotFoundError, ValueError):
        return None


def effective_methods_manifest(*, file_names: list[str], reader_type: str, activity_mapping: dict,
                               settings: dict, analysis_config: dict, data_quality: dict,
                               provenance: dict, participant_join: dict | None = None,
                               csv_mapping: dict | None = None, csv_separator: str = ",",
                               results: dict | None = None) -> dict:
    """Always store resolved defaults AND overrides (never only user changes)."""
    from .activity_mapping import normalize_activity_signal_settings
    from .data_quality import resolve_data_quality_settings
    from .raw_signal_processing import DEFAULT_RAW_SIGNAL

    requested = (activity_mapping or {}).get("requested", "auto")
    effective_signal = normalize_activity_signal_settings(settings, requested)
    return {
        "schema_version": "actilab-reproducibility-1.0",
        "exported_at_utc": datetime.now(timezone.utc).isoformat(),
        "files": file_names,
        "detected_reader": reader_type,
        "participant_join": participant_join or {"joined": False},
        "activity_mapping": activity_mapping,
        "effective_activity_signal_settings": effective_signal,
        "raw_signal_defaults": dict(DEFAULT_RAW_SIGNAL),
        "effective_quality_settings": (data_quality or {}).get("settings") or resolve_data_quality_settings((analysis_config or {}).get("supportFileSettings")),
        "effective_analysis_config": analysis_config or {},
        "tabular_column_mapping": csv_mapping or {},
        "tabular_separator": csv_separator,
        "data_quality": {key: value for key, value in (data_quality or {}).items() if key != "daily_qc"},
        "processing_provenance": provenance or {},
        "result_metric_ids": list((results or {}).keys()),
        "software_versions": {name: _version(name) for name in ("pyActigraphy", "numpy", "pandas", "scipy", "pygt3x", "accelerometer", "fastapi")},
        "reference": {
            "ggir_raw_processing": "https://wadpac.github.io/GGIR/articles/chapter4_AccMetrics.html",
            "ggir_sleep_settings": "https://wadpac.github.io/GGIR/articles/GGIRParameters.html",
            "pyactigraphy_metrics": "https://ghammad.github.io/pyActigraphy/MetricsMixin.html",
        },
        "compatibility_note": "ActiLab's existing raw acceleration and pyActigraphy scoring paths are not GGIR-equivalent. GGIR HDCZA/SIB is not silently substituted for existing algorithms. A separate benchmark is required.",
    }
