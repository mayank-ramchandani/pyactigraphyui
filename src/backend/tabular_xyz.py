"""Transparent raw XYZ-CSV epoch aggregation without pretending vendor calibration.

Supported only with explicit or unambiguous acceleration units. This is an
import conversion convenience, NOT GGIR calibration or HDCZA sleep scoring.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .io_helpers import build_baseraw_from_dataframe, _coerce_localized_numeric
from .activity_mapping import attach_mapping_metadata, mapping_metadata


AXIS_ALIASES = {
    "x_col": ("x_g", "acc_x_g", "accelerometer_x_g", "x_mg", "x_ms2", "acc_x", "accel_x", "acceleration_x", "x"),
    "y_col": ("y_g", "acc_y_g", "accelerometer_y_g", "y_mg", "y_ms2", "acc_y", "accel_y", "acceleration_y", "y"),
    "z_col": ("z_g", "acc_z_g", "accelerometer_z_g", "z_mg", "z_ms2", "acc_z", "accel_z", "acceleration_z", "z"),
}


def detect_xyz_mapping(columns):
    lookup = {str(name).lower().replace(" ", "").replace("-", "_"): str(name) for name in columns}
    resolved = {}
    for axis, variants in AXIS_ALIASES.items():
        resolved[axis] = next((lookup[v] for v in variants if v in lookup), None)
    units = None
    if all(resolved.values()):
        names = [str(v).lower().replace(" ", "") for v in resolved.values()]
        if all(n.endswith("_mg") for n in names):
            units = "mg"
        elif all(n.endswith(("_ms2", "_m_s2")) for n in names):
            units = "m_s2"
        elif all(n.endswith("_g") for n in names):
            units = "g"
    return {**resolved, "acceleration_unit": units}


def load_xyz_as_baseraw(dataframe: pd.DataFrame, mapping: dict, *, name: str, epoch_seconds: int = 30, activity_mapping: str = "auto", signal_settings: dict | None = None):
    cols = [mapping.get(key) for key in ("x_col", "y_col", "z_col")]
    if any(not c or c not in dataframe for c in cols):
        raise ValueError("Map all three raw acceleration columns (X, Y and Z).")
    unit = mapping.get("acceleration_unit")
    if unit not in {"g", "mg", "m_s2"}:
        raise ValueError("Specify acceleration units (g, mg or m/s²) for all XYZ columns; units cannot safely be guessed.")
    factor = {"g": 1.0, "mg": 1 / 1000, "m_s2": 1 / 9.80665}[unit]
    time_col = mapping.get("timestamp_col")
    if not time_col or time_col not in dataframe:
        raise ValueError("Raw XYZ CSV requires a timestamp column.")
    timestamp_str = dataframe[time_col].astype(str).str.strip()
    other_time = mapping.get("time_col")
    if other_time and other_time in dataframe:
        timestamp_str += " " + dataframe[other_time].astype(str).str.strip()
    times = pd.to_datetime(timestamp_str, errors="coerce", dayfirst=bool(mapping.get("dayfirst", False)))
    xyz = np.column_stack([_coerce_localized_numeric(dataframe[c]).to_numpy(dtype=float) for c in cols]) * factor
    frame = pd.DataFrame(xyz, columns=["x_g", "y_g", "z_g"], index=pd.DatetimeIndex(times))
    frame = frame.loc[frame.index.notna()].sort_index()
    frame = frame.loc[~frame.index.duplicated(keep="first")]
    frame = frame.replace([np.inf, -np.inf], np.nan).dropna(subset=["x_g", "y_g", "z_g"])
    if len(frame) < 2:
        raise ValueError("Raw XYZ CSV requires at least two timestamped valid three-axis samples.")
    if len(frame) > 5_000_000:
        raise ValueError("XYZ CSV contains over 5 million samples; convert large recordings to a supported streaming format first.")
    period = int(epoch_seconds)
    deltas = frame.index.to_series().diff().dropna().dt.total_seconds()
    deltas = deltas[deltas > 0]
    sample_seconds = float(deltas.median())
    if not np.isfinite(sample_seconds) or sample_seconds <= 0:
        raise ValueError("Cannot estimate sample rate from the XYZ timestamps.")
    if sample_seconds > period:
        raise ValueError(f"XYZ sample spacing ({sample_seconds:g}s) exceeds chosen {period}s epoch; choose an appropriate epoch length.")
    vm = np.sqrt((frame[["x_g", "y_g", "z_g"]] ** 2).sum(axis=1))
    deviation = (vm - 1.0) * 1000
    positive = deviation.clip(lower=0)
    metric = str(activity_mapping or "auto").lower()
    rule = f"{period}s"
    if metric in {"auto", "original", "enmo", "accelerometer"}:
        values = positive.resample(rule).mean()
        resolved = "enmo"
    elif metric == "mad":
        values = vm.groupby(pd.Grouper(freq=rule)).transform("mean")
        values = ((vm - values).abs() * 1000).resample(rule).mean()
        resolved = "mad"
    elif metric == "pim":
        values = (deviation.abs() * sample_seconds).resample(rule).sum(min_count=1)
        resolved = "pim"
    elif metric in {"zcm", "tat"}:
        config = signal_settings or {}
        if config.get("threshold_method", "adaptive") != "fixed":
            raise ValueError("XYZ CSV ZCM/TAT requires a fixed milligravity threshold; choose Fixed in activity settings.")
        threshold = config.get("threshold_mg")
        if threshold is None:
            raise ValueError("XYZ CSV ZCM/TAT requires a threshold in mg.")
        above = deviation.abs() > float(threshold)
        if metric == "tat":
            values = (above.astype(float) * sample_seconds).resample(rule).sum(min_count=1)
        else:
            # Count changes *within* epochs, not at recording/epoch boundaries.
            bucket = frame.index.floor(rule)
            changes = above.ne(above.shift(1)) & (bucket == pd.Series(bucket, index=frame.index).shift(1))
            values = changes.astype(float).resample(rule).sum(min_count=1)
        resolved = metric
    else:
        raise ValueError(f"XYZ CSV cannot derive mapping: {metric}.")
    values = values.asfreq(rule)
    output = pd.DataFrame({"activity": values})
    for field, mapped in (("light_col", "light__LIGHT"), ("temperature_col", "temperature"), ("nonwear_col", "nonwear")):
        source_col = mapping.get(field)
        if source_col and source_col in dataframe:
            sensor = pd.Series(_coerce_localized_numeric(dataframe[source_col]).to_numpy(), index=pd.DatetimeIndex(times)).dropna()
            output[mapped] = sensor.resample(rule).mean().reindex(output.index)
            if field == "nonwear_col":
                output.attrs["nonwear_source_column"] = source_col
    raw = build_baseraw_from_dataframe(output, name=name, uuid="xyz-csv-import")
    raw._ui_tabular_xyz_info = {
        "axis_columns": cols, "input_unit": unit,
        "estimated_sample_seconds": sample_seconds, "output_epoch_seconds": period,
        "auto_calibration_applied": False,
        "sleep_angle_series_available": False,
    }
    return attach_mapping_metadata(raw, mapping_metadata(
        metric, resolved, source="csv_xyz_unautomatically_calibrated",
        units={"enmo": "mg", "mad": "mg", "pim": "mg·s/epoch", "zcm": "crossings/epoch", "tat": "s/epoch"}[resolved],
        note="Mapped XYZ converted to epoch metrics; no auto-calibration and no GGIR-style angle-based sleep scoring. Input acceleration unit was explicit or unambiguous.",
        source_axes=cols, source_unit=unit, epoch_seconds=period,
    ))
