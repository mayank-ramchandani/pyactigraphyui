"""ActiGraph .gt3x loading through pygt3x, with optional ActiLife-style counts.

This module avoids the .gt3x -> .agd requirement. It reads calibrated raw X/Y/Z
samples with ActiGraph's pygt3x package and then builds a pyActigraphy BaseRaw
object from either:

1. ActiLife-style epoch counts via ActiGraph's Python agcounts package; or
2. ENMO/vector-magnitude epoch summaries as a fallback.

The counts path is preferred for pyActigraphy algorithms whose thresholds expect
ActiGraph-style counts. The ENMO path is useful for quick previews and
non-parametric rest/activity metrics, but thresholds must be interpreted as mg,
not counts.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import numpy as np
import pandas as pd

try:
    from pyActigraphy.io import BaseRaw
except Exception:  # pragma: no cover - depends on deployment environment
    BaseRaw = None


DEFAULT_GT3X_EPOCH_PERIOD = int(os.environ.get("GT3X_EPOCH_PERIOD", os.environ.get("ACCELEROMETER_EPOCH_PERIOD", "30")))
DEFAULT_GT3X_SAMPLE_RATE = float(os.environ.get("GT3X_DEFAULT_SAMPLE_RATE", "30"))
DEFAULT_GT3X_ACTIVITY_MODE = os.environ.get("GT3X_ACTIVITY_MODE", "counts").strip().lower()


class GT3XProcessingError(ValueError):
    """Raised when .gt3x loading or conversion fails."""


def _normalise_column_name(name: Any) -> str:
    return str(name).strip().lower().replace(" ", "").replace("_", "").replace("-", "")


def _get_nested_attr(obj: Any, attr_names: list[str]) -> Any:
    for attr_name in attr_names:
        current = obj
        ok = True
        for part in attr_name.split("."):
            if hasattr(current, part):
                current = getattr(current, part)
            else:
                ok = False
                break
        if ok and current is not None:
            return current
    return None


def _coerce_sample_rate(value: Any, fallback: float = DEFAULT_GT3X_SAMPLE_RATE) -> float:
    if value is None:
        return float(fallback)
    try:
        if isinstance(value, str):
            value = value.lower().replace("hz", "").replace("sample_rate", "").strip()
        rate = float(value)
        return rate if rate > 0 else float(fallback)
    except Exception:
        return float(fallback)


def _pick_timestamp_column(df: pd.DataFrame) -> Optional[str]:
    lookup = {_normalise_column_name(c): c for c in df.columns}
    for candidate in [
        "timestamp",
        "HEADER_TIMESTAMP",
        "header_timestamp",
        "time",
        "datetime",
        "date_time",
        "DateTime",
        "TimeStamp",
    ]:
        found = lookup.get(_normalise_column_name(candidate))
        if found is not None:
            return str(found)
    return None


def _pick_axis_columns(df: pd.DataFrame) -> list[str]:
    numeric_df = df.select_dtypes(include="number")
    lookup = {_normalise_column_name(c): c for c in numeric_df.columns}
    axis_sets = [
        ("X", "Y", "Z"),
        ("x", "y", "z"),
        ("axis1", "axis2", "axis3"),
        ("axisx", "axisy", "axisz"),
        ("xaxis", "yaxis", "zaxis"),
        ("accelx", "accely", "accelz"),
        ("accelerometerx", "accelerometery", "accelerometerz"),
    ]
    for names in axis_sets:
        if all(_normalise_column_name(name) in lookup for name in names):
            return [str(lookup[_normalise_column_name(name)]) for name in names]
    if numeric_df.shape[1] >= 3:
        return [str(c) for c in numeric_df.columns[:3]]
    raise GT3XProcessingError(
        "The .gt3x file was read with pygt3x, but X/Y/Z acceleration columns could not be identified."
    )


def _build_uniform_index(n_rows: int, start_time: Any, sample_rate: float) -> pd.DatetimeIndex:
    start = pd.to_datetime(start_time, errors="coerce") if start_time is not None else pd.NaT
    if pd.isna(start):
        start = pd.Timestamp("2000-01-01 00:00:00")
    step_ns = int(1_000_000_000 / max(float(sample_rate), 1e-9))
    return pd.date_range(start=start, periods=int(n_rows), freq=pd.to_timedelta(step_ns, unit="ns"))


def _extract_metadata(reader: Any, file_path: str) -> Dict[str, Any]:
    metadata = {
        "_source": "gt3x_pygt3x",
        "_source_file": Path(file_path).name,
        "idle_sleep_mode_activated": getattr(reader, "idle_sleep_mode_activated", None),
    }
    for key, attr_names in {
        "start_time": ["start_time", "start_datetime", "start_date", "info.start_time", "info.start_datetime", "metadata.start_time"],
        "sample_rate": ["sample_rate", "sampling_rate", "frequency", "fs", "info.sample_rate", "info.sampling_rate", "metadata.sample_rate"],
        "serial_number": ["serial_number", "device_serial_number", "info.serial_number", "metadata.serial_number"],
        "device": ["device", "device_name", "info.device", "metadata.device"],
    }.items():
        value = _get_nested_attr(reader, attr_names)
        if value is not None:
            metadata[key] = str(value)
    return metadata


def read_gt3x_dataframe(file_path: str) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    try:
        from pygt3x.reader import FileReader
    except Exception as exc:  # pragma: no cover - depends on deployment environment
        raise GT3XProcessingError(
            "Direct .gt3x loading requires pygt3x. Add `pygt3x==0.7.1` to the backend requirements "
            "and redeploy the server."
        ) from exc

    try:
        with FileReader(file_path) as reader:
            df = reader.to_pandas()
            metadata = _extract_metadata(reader, file_path)
            try:
                temp_df = reader.temperature_to_pandas()
                metadata["temperature_rows"] = int(len(temp_df)) if temp_df is not None else 0
            except Exception:
                metadata["temperature_rows"] = 0
    except Exception as exc:
        raise GT3XProcessingError(
            "Could not read this .gt3x file with pygt3x. Confirm the file is not corrupted and was exported/downloaded as a raw ActiGraph GT3X archive. "
            f"Original error: {exc}"
        ) from exc

    if df is None or len(df) == 0:
        raise GT3XProcessingError("The .gt3x file was read, but no acceleration samples were returned.")

    return df.copy(), metadata


def _prepare_raw_axes(df: pd.DataFrame, metadata: Dict[str, Any]) -> Tuple[pd.DataFrame, float, Optional[str], list[str]]:
    axes = _pick_axis_columns(df)
    timestamp_col = _pick_timestamp_column(df)
    sample_rate = _coerce_sample_rate(metadata.get("sample_rate"), fallback=DEFAULT_GT3X_SAMPLE_RATE)

    raw = df[axes].apply(pd.to_numeric, errors="coerce").dropna(how="any").astype("float32")
    if raw.empty:
        raise GT3XProcessingError("The .gt3x file did not contain enough valid numeric X/Y/Z samples.")

    if timestamp_col and timestamp_col in df.columns:
        parsed = pd.to_datetime(df.loc[raw.index, timestamp_col], errors="coerce")
        if parsed.notna().sum() >= 2 and parsed.nunique() > 1:
            raw.index = parsed
            raw = raw.loc[raw.index.notna()].sort_index()
            median_step = pd.Series(raw.index).diff().dropna().median()
            if pd.notna(median_step) and median_step.total_seconds() > 0:
                sample_rate = 1.0 / median_step.total_seconds()
        else:
            raw.index = _build_uniform_index(len(raw), metadata.get("start_time"), sample_rate)
    elif isinstance(df.index, pd.DatetimeIndex):
        raw.index = df.loc[raw.index].index
    else:
        raw.index = _build_uniform_index(len(raw), metadata.get("start_time"), sample_rate)

    raw.columns = ["X", "Y", "Z"]
    return raw, sample_rate, timestamp_col, axes


def _counts_activity_from_axes(raw_axes: pd.DataFrame, sample_rate: float, epoch_period: int) -> Tuple[pd.Series, Dict[str, Any]]:
    try:
        from agcounts.extract import get_counts
    except Exception as exc:  # pragma: no cover - depends on deployment environment
        raise GT3XProcessingError(
            "ActiLife-style counts require the Python `agcounts` package. Add `agcounts==0.2.6`, or set GT3X_ACTIVITY_MODE=enmo."
        ) from exc

    raw_array = raw_axes[["X", "Y", "Z"]].to_numpy(dtype=np.float32, copy=True)
    counts = get_counts(
        raw_array,
        freq=int(round(sample_rate)),
        epoch=int(epoch_period),
        fast=True,
    )
    del raw_array

    counts_df = pd.DataFrame(counts, columns=["Axis1", "Axis2", "Axis3"])
    activity = np.sqrt((counts_df[["Axis1", "Axis2", "Axis3"]].astype(float) ** 2).sum(axis=1))
    start = pd.to_datetime(raw_axes.index[0]).floor(f"{int(epoch_period)}s")
    activity.index = pd.date_range(start=start, periods=len(activity), freq=pd.to_timedelta(epoch_period, unit="s"))
    return activity.rename("activity_counts_vm"), {
        "_gt3x_activity_mode": "counts",
        "_gt3x_counts_axes": ["Axis1", "Axis2", "Axis3"],
    }


def _enmo_activity_from_axes(raw_axes: pd.DataFrame, epoch_period: int) -> Tuple[pd.Series, Dict[str, Any]]:
    axes = raw_axes[["X", "Y", "Z"]].astype(float)
    vm = np.sqrt((axes ** 2).sum(axis=1))
    # If values look like g-units, convert VM to ENMO mg; otherwise keep vector magnitude.
    if pd.Series(vm).quantile(0.95) < 16:
        activity = ((pd.Series(vm, index=raw_axes.index) - 1.0).clip(lower=0) * 1000.0).rename("ENMO_mg")
        mode = "enmo_mg"
    else:
        activity = pd.Series(vm, index=raw_axes.index).rename("vector_magnitude")
        mode = "vector_magnitude"
    activity = activity.resample(pd.to_timedelta(epoch_period, unit="s")).mean().dropna()
    return activity, {"_gt3x_activity_mode": mode}


def prepare_gt3x_activity_series(
    file_path: str,
    epoch_period: int = DEFAULT_GT3X_EPOCH_PERIOD,
    activity_mode: str = DEFAULT_GT3X_ACTIVITY_MODE,
) -> Tuple[pd.Series, Dict[str, Any], pd.DataFrame]:
    df, metadata = read_gt3x_dataframe(file_path)
    raw_axes, sample_rate, timestamp_col, axes = _prepare_raw_axes(df, metadata)

    mode = (activity_mode or "counts").strip().lower()
    mode_meta: Dict[str, Any]
    try:
        if mode == "counts":
            activity, mode_meta = _counts_activity_from_axes(raw_axes, sample_rate, epoch_period)
        elif mode in {"enmo", "enmo_mg", "vm", "vector_magnitude"}:
            activity, mode_meta = _enmo_activity_from_axes(raw_axes, epoch_period)
        else:
            raise GT3XProcessingError(f"Unsupported GT3X_ACTIVITY_MODE: {activity_mode}")
    except Exception as exc:
        if mode == "counts":
            activity, mode_meta = _enmo_activity_from_axes(raw_axes, epoch_period)
            mode_meta["_gt3x_counts_fallback_reason"] = str(exc)
        else:
            raise

    if len(activity) < 2:
        raise GT3XProcessingError("The .gt3x conversion produced fewer than two valid activity epochs.")

    metadata.update(mode_meta)
    metadata.update(
        {
            "_epoch_period_seconds": int(epoch_period),
            "_sample_rate_hz": float(sample_rate),
            "_timestamp_column": timestamp_col,
            "_axis_columns": axes,
            "_raw_rows": int(len(raw_axes)),
            "_raw_columns": [str(c) for c in df.columns],
        }
    )
    return activity.astype(float).sort_index(), metadata, df


def load_gt3x_as_baseraw(
    file_path: str,
    epoch_period: int = DEFAULT_GT3X_EPOCH_PERIOD,
    activity_mode: str = DEFAULT_GT3X_ACTIVITY_MODE,
):
    if BaseRaw is None:
        raise GT3XProcessingError("pyActigraphy.io.BaseRaw is not available in this backend environment.")

    activity, metadata, _ = prepare_gt3x_activity_series(
        file_path,
        epoch_period=epoch_period,
        activity_mode=activity_mode,
    )

    raw = BaseRaw(
        name=Path(file_path).stem,
        uuid=str(metadata.get("serial_number") or Path(file_path).stem),
        format="ActiGraph GT3X via pygt3x/agcounts",
        axial_mode=None,
        start_time=activity.index[0],
        period=activity.index[-1] - activity.index[0],
        frequency=pd.to_timedelta(epoch_period, unit="s"),
        data=activity,
        light=None,
    )
    raw._ui_gt3x_summary = metadata
    raw._ui_source_format = "gt3x_pygt3x"
    return raw


def summarize_gt3x_file(
    file_path: str,
    epoch_period: int = DEFAULT_GT3X_EPOCH_PERIOD,
    activity_mode: str = DEFAULT_GT3X_ACTIVITY_MODE,
) -> Dict[str, Any]:
    activity, metadata, df = prepare_gt3x_activity_series(
        file_path,
        epoch_period=epoch_period,
        activity_mode=activity_mode,
    )
    return {
        "rows": int(len(df)),
        "valid_activity_rows": int(len(activity)),
        "columns": [str(c) for c in df.columns],
        "activity_column": str(activity.name),
        "start_time": activity.index[0].isoformat(),
        "end_time": activity.index[-1].isoformat(),
        "frequency": str(pd.to_timedelta(epoch_period, unit="s")),
        "activity_mean": float(activity.mean()),
        "activity_min": float(activity.min()),
        "activity_max": float(activity.max()),
        "activity_nonzero_fraction": float((activity > 0).mean()),
        "light_available": False,
        "first_rows": df.head(5).astype(str).to_dict(orient="records"),
        "gt3x_summary": metadata,
    }
