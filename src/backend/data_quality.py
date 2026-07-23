"""Shared missing-data, non-wear, and valid-day preprocessing.

All supported readers eventually expose one timestamp-indexed activity series,
but they do not expose gaps and masks in exactly the same way.  This module
normalizes those representations before any activity or sleep metric is run.

The important invariant is:

* missing recording epochs are NaN, never zero;
* detected/mapped non-wear and explicit mask intervals are excluded;
* days below the configured analyzable-hours threshold remain on the timeline
  but are fully masked;
* the same final validity mask is used by activity and sleep calculations.
"""

from __future__ import annotations

import copy
import math
import warnings
from typing import Any, Dict, Iterable, Optional, Tuple

import numpy as np
import pandas as pd

try:  # Optional in lightweight unit-test environments.
    from pyActigraphy.io import BaseRaw
except Exception:  # pragma: no cover - deployment installs pyActigraphy
    BaseRaw = None


DEFAULT_MIN_VALID_HOURS_PER_DAY = 16.0
DEFAULT_MIN_VALID_DAYS_FOR_RHYTHM = 2
DEFAULT_MIN_SLEEP_WINDOW_COVERAGE = 0.80


def _finite_number(value: Any, default: float, minimum: float, maximum: float) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError):
        return default
    if not math.isfinite(number):
        return default
    return min(max(number, minimum), maximum)


def resolve_data_quality_settings(support_settings: Optional[dict] = None) -> Dict[str, Any]:
    """Return validated settings from the existing masking configuration."""

    support_settings = support_settings or {}
    masking = support_settings.get("masking", support_settings) or {}

    customize_value = masking.get("customizeDataQualityThresholds")
    if customize_value is None:
        # Backward compatibility for saved/API configurations created before
        # the explicit opt-in toggle existed.
        customize_thresholds = any(
            key in masking
            for key in (
                "minimumValidHoursPerDay",
                "minimumValidDaysForRhythm",
                "minimumSleepWindowCoverage",
                "minimumSleepWindowCoveragePercent",
            )
        )
    else:
        customize_thresholds = bool(customize_value)

    threshold_source = masking if customize_thresholds else {}
    min_valid_hours = _finite_number(
        threshold_source.get("minimumValidHoursPerDay", DEFAULT_MIN_VALID_HOURS_PER_DAY),
        DEFAULT_MIN_VALID_HOURS_PER_DAY,
        1.0,
        24.0,
    )
    try:
        min_valid_days = int(
            threshold_source.get("minimumValidDaysForRhythm", DEFAULT_MIN_VALID_DAYS_FOR_RHYTHM)
        )
    except (TypeError, ValueError, OverflowError):
        min_valid_days = DEFAULT_MIN_VALID_DAYS_FOR_RHYTHM
    min_valid_days = min(max(min_valid_days, 1), 365)

    sleep_coverage_value = threshold_source.get("minimumSleepWindowCoverage")
    if sleep_coverage_value in (None, ""):
        percent = threshold_source.get("minimumSleepWindowCoveragePercent")
        sleep_coverage_value = float(percent) / 100.0 if percent not in (None, "") else DEFAULT_MIN_SLEEP_WINDOW_COVERAGE
    min_sleep_coverage = _finite_number(
        sleep_coverage_value,
        DEFAULT_MIN_SLEEP_WINDOW_COVERAGE,
        0.0,
        1.0,
    )

    return {
        "respect_detected_nonwear": bool(masking.get("respectNonwear", True)),
        "customize_data_quality_thresholds": customize_thresholds,
        "minimum_valid_hours_per_day": min_valid_hours,
        # Keep the legacy key for exported-config compatibility while making
        # the actual rule explicitly consecutive.
        "minimum_valid_days_for_rhythm": min_valid_days,
        "minimum_consecutive_valid_days_for_rhythm": min_valid_days,
        "minimum_sleep_window_coverage": min_sleep_coverage,
    }


def _numeric_activity_series(raw: Any) -> pd.Series:
    """Read activity without dropping NaNs or applying a reader-specific mask."""

    data = None
    try:
        data = getattr(raw, "raw_data", None)
    except Exception:
        data = None
    if data is None:
        data = getattr(raw, "data", None)
    if data is None:
        raise ValueError("The loaded recording does not expose an activity series for data-quality processing.")

    if isinstance(data, pd.DataFrame):
        numeric_columns = data.select_dtypes(include="number").columns.tolist()
        preferred = ["VM", "vm", "activity", "Activity", "data", "counts", "acc", "ACC_mg", "ENMO_mg", "MAD_mg"]
        selected = next((column for column in preferred if column in data.columns), None)
        if selected is None and numeric_columns:
            selected = numeric_columns[0]
        if selected is None:
            raise ValueError("The loaded recording does not contain a numeric activity channel.")
        data = data[selected]
    elif not isinstance(data, pd.Series):
        data = pd.Series(data)

    series = pd.to_numeric(data, errors="coerce").copy()
    if not isinstance(series.index, pd.DatetimeIndex):
        series.index = pd.to_datetime(series.index, errors="coerce")
    series = series.loc[~pd.isna(series.index)].sort_index()
    if series.index.has_duplicates:
        series = series.groupby(level=0).mean()
    if len(series) < 2:
        raise ValueError("Fewer than two timestamped activity epochs remain before data-quality processing.")
    return series


def _positive_median_step(index: pd.DatetimeIndex) -> Optional[pd.Timedelta]:
    try:
        deltas = index.to_series().diff().dropna()
        deltas = deltas[deltas > pd.Timedelta(0)]
        if len(deltas):
            return pd.Timedelta(deltas.median())
    except Exception:
        pass
    return None


def _recording_frequency(raw: Any, series: pd.Series) -> pd.Timedelta:
    candidates = [getattr(series.index, "freq", None), getattr(raw, "frequency", None)]
    try:
        candidates.append(pd.infer_freq(series.index))
    except Exception:
        pass
    candidates.append(_positive_median_step(series.index))
    for candidate in candidates:
        if candidate in (None, ""):
            continue
        try:
            delta = pd.Timedelta(candidate)
            if delta > pd.Timedelta(0):
                return delta
        except Exception:
            continue
    raise ValueError("Could not determine the epoch duration needed for missing-data quality control.")


def _timestamp_for_index(value: Any, index: pd.DatetimeIndex) -> pd.Timestamp:
    timestamp = pd.Timestamp(value)
    index_tz = getattr(index, "tz", None)
    if index_tz is None and timestamp.tzinfo is not None:
        timestamp = timestamp.tz_convert(None)
    elif index_tz is not None and timestamp.tzinfo is None:
        timestamp = timestamp.tz_localize(index_tz)
    elif index_tz is not None and timestamp.tzinfo is not None:
        timestamp = timestamp.tz_convert(index_tz)
    return timestamp


def _requested_recording_bounds(raw: Any, index: pd.DatetimeIndex) -> Tuple[pd.Timestamp, pd.Timestamp]:
    start = getattr(raw, "_ui_analysis_start", None)
    stop = getattr(raw, "_ui_analysis_stop", None)
    start_ts = _timestamp_for_index(start, index) if start not in (None, "") else index.min()
    stop_ts = _timestamp_for_index(stop, index) if stop not in (None, "") else index.max()
    return max(start_ts, index.min()), min(stop_ts, index.max())


def _regularize_series(raw: Any, series: pd.Series) -> Tuple[pd.Series, pd.Timedelta]:
    frequency = _recording_frequency(raw, series)
    start, stop = _requested_recording_bounds(raw, series.index)
    if stop <= start:
        raise ValueError("The selected recording start/stop interval contains fewer than two activity epochs.")
    scoped = series.loc[start:stop]
    if len(scoped) < 2:
        raise ValueError("The selected recording start/stop interval contains fewer than two activity epochs.")
    full_index = pd.date_range(start=scoped.index.min(), end=scoped.index.max(), freq=frequency)
    regular = scoped.reindex(full_index)
    regular.name = series.name or "activity"
    return regular, frequency


def _reader_mask(raw: Any, index: pd.DatetimeIndex) -> Optional[pd.Series]:
    """Return an existing reader/mapped wear mask without creating a new one."""

    try:
        inactivity_length = getattr(raw, "inactivity_length", None)
    except Exception:
        inactivity_length = None

    # Accessing BaseRaw.mask with no configured/existing mask only emits a
    # warning and returns None.  Suppress that warning at this inspection point.
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            mask = getattr(raw, "mask", None)
    except Exception:
        mask = None

    if mask is None and inactivity_length is None:
        return None
    if isinstance(mask, pd.DataFrame):
        mask = mask.iloc[:, 0] if mask.shape[1] else None
    if mask is None:
        return None
    if not isinstance(mask, pd.Series):
        try:
            mask = pd.Series(mask, index=getattr(raw, "raw_data", getattr(raw, "data", None)).index)
        except Exception:
            return None
    numeric = pd.to_numeric(mask, errors="coerce")
    if not isinstance(numeric.index, pd.DatetimeIndex):
        numeric.index = pd.to_datetime(numeric.index, errors="coerce")
    numeric = numeric.loc[~pd.isna(numeric.index)]
    if numeric.index.has_duplicates:
        numeric = numeric.groupby(level=0).min()
    return numeric.reindex(index).fillna(0) > 0


def _manual_interval_mask(index: pd.DatetimeIndex, intervals: Iterable[dict]) -> pd.Series:
    valid = pd.Series(True, index=index, dtype=bool)
    for interval in intervals or []:
        try:
            start = _timestamp_for_index(interval.get("start"), index)
            stop = _timestamp_for_index(interval.get("stop"), index)
        except Exception:
            continue
        if stop <= start:
            continue
        valid.loc[(valid.index >= start) & (valid.index <= stop)] = False
    return valid


def _rounded_hours(epoch_count: int, epoch_hours: float) -> float:
    return round(float(epoch_count) * epoch_hours, 4)


def _longest_consecutive_day_run(days: Iterable[pd.Timestamp]) -> int:
    normalized = sorted({pd.Timestamp(day).normalize() for day in days})
    if not normalized:
        return 0
    longest = current = 1
    for previous, day in zip(normalized, normalized[1:]):
        if day - previous == pd.Timedelta(days=1):
            current += 1
            longest = max(longest, current)
        else:
            current = 1
    return longest


def _daily_quality_table(
    series: pd.Series,
    native_wear: pd.Series,
    manual_wear: pd.Series,
    frequency: pd.Timedelta,
    minimum_valid_hours: float,
) -> Tuple[list[dict], pd.Series, list[pd.Timestamp]]:
    raw_recorded = series.notna() & np.isfinite(series)
    detected_nonwear = raw_recorded & ~native_wear
    manually_masked = raw_recorded & native_wear & ~manual_wear
    analyzable = raw_recorded & native_wear & manual_wear
    epoch_hours = frequency.total_seconds() / 3600.0

    first_day = series.index.min().normalize()
    last_day = series.index.max().normalize()
    days = pd.date_range(first_day, last_day, freq="1D")
    rows: list[dict] = []
    valid_days: list[pd.Timestamp] = []

    for day in days:
        next_day = day + pd.Timedelta(days=1)
        in_day = (series.index >= day) & (series.index < next_day)
        recorded_hours = _rounded_hours(int(raw_recorded.loc[in_day].sum()), epoch_hours)
        nonwear_hours = _rounded_hours(int(detected_nonwear.loc[in_day].sum()), epoch_hours)
        manual_hours = _rounded_hours(int(manually_masked.loc[in_day].sum()), epoch_hours)
        analyzable_hours = _rounded_hours(int(analyzable.loc[in_day].sum()), epoch_hours)
        missing_hours = round(max(0.0, 24.0 - recorded_hours), 4)
        is_valid = analyzable_hours + 1e-9 >= minimum_valid_hours
        if is_valid:
            valid_days.append(day)

        reasons = []
        if not is_valid:
            reasons.append(
                f"analyzable coverage {analyzable_hours:g} h is below the {minimum_valid_hours:g} h threshold"
            )
        if recorded_hours == 0:
            reasons.append("no recording data")

        rows.append(
            {
                "date": day.date().isoformat(),
                "expected_hours": 24.0,
                "recorded_hours": recorded_hours,
                "recording_gap_hours": missing_hours,
                "detected_nonwear_hours": nonwear_hours,
                "manual_mask_hours": manual_hours,
                "analyzable_hours": analyzable_hours,
                "valid_day": bool(is_valid),
                "exclusion_reason": "; ".join(reasons) if reasons else None,
            }
        )

    valid_day_set = {day.date() for day in valid_days}
    valid_day_mask = pd.Series(
        [timestamp.date() in valid_day_set for timestamp in series.index],
        index=series.index,
        dtype=bool,
    )
    return rows, analyzable & valid_day_mask, valid_days


def _copy_ui_metadata(source: Any, target: Any) -> None:
    try:
        for key, value in vars(source).items():
            if key.startswith("_ui_"):
                setattr(target, key, value)
    except Exception:
        pass


def _analysis_raw_with_mask(raw: Any, series: pd.Series, mask: pd.Series, frequency: pd.Timedelta) -> Any:
    """Create an analysis object whose metrics all see the same strict mask."""

    if BaseRaw is not None and isinstance(raw, BaseRaw):
        light = None
        try:
            light = getattr(raw, "raw_light", None)
        except Exception:
            light = getattr(raw, "light", None)
        analysis_raw = BaseRaw(
            name=str(getattr(raw, "name", "Recording")),
            uuid=str(getattr(raw, "uuid", "recording")),
            format=str(getattr(raw, "format", "Pandas")),
            axial_mode=getattr(raw, "axial_mode", None),
            start_time=series.index[0],
            period=series.index[-1] - series.index[0],
            frequency=frequency,
            data=series,
            light=light,
            fpath=getattr(raw, "fpath", None),
        )
        _copy_ui_metadata(raw, analysis_raw)
        try:
            analysis_raw.display_name = getattr(raw, "display_name", getattr(raw, "name", "Recording"))
        except Exception:
            pass
    else:
        analysis_raw = copy.copy(raw)
        try:
            analysis_raw.data = series.where(mask)
        except Exception as exc:
            raise ValueError(f"This recording type does not allow the cleaned activity series to be attached: {exc}") from exc
        _copy_ui_metadata(raw, analysis_raw)

    try:
        analysis_raw.mask = mask.astype(int)
        analysis_raw.mask_inactivity = True
        analysis_raw.exclude_if_mask = True
    except Exception:
        # Lightweight raw objects use the already-masked ``data`` assignment.
        pass
    return analysis_raw


def apply_data_quality_control(raw: Any, support_settings: Optional[dict] = None) -> Tuple[Any, Dict[str, Any]]:
    """Apply common missingness/non-wear rules and return ``(raw, QC payload)``."""

    settings = resolve_data_quality_settings(support_settings)
    source = _numeric_activity_series(raw)
    regular, frequency = _regularize_series(raw, source)

    existing_mask = _reader_mask(raw, regular.index) if settings["respect_detected_nonwear"] else None
    native_wear = existing_mask if existing_mask is not None else pd.Series(True, index=regular.index, dtype=bool)
    manual_intervals = getattr(raw, "_ui_mask_intervals", None) or []
    manual_wear = _manual_interval_mask(regular.index, manual_intervals)

    daily_rows, final_mask, valid_days = _daily_quality_table(
        regular,
        native_wear=native_wear,
        manual_wear=manual_wear,
        frequency=frequency,
        minimum_valid_hours=settings["minimum_valid_hours_per_day"],
    )
    analysis_raw = _analysis_raw_with_mask(raw, regular, final_mask, frequency)

    invalid_days = [row for row in daily_rows if not row["valid_day"]]
    completely_missing_days = [row for row in daily_rows if row["recorded_hours"] == 0]
    detected_nonwear_hours = round(sum(row["detected_nonwear_hours"] for row in daily_rows), 4)
    manual_mask_hours = round(sum(row["manual_mask_hours"] for row in daily_rows), 4)
    gap_hours = round(sum(row["recording_gap_hours"] for row in daily_rows), 4)

    qc_warnings = []
    if invalid_days:
        qc_warnings.append(
            f"Excluded {len(invalid_days)} day(s) with less than {settings['minimum_valid_hours_per_day']:g} analyzable hours."
        )
    if completely_missing_days:
        qc_warnings.append(
            f"Found {len(completely_missing_days)} completely unrecorded day(s); they remain missing and do not become zero activity."
        )
    longest_consecutive_valid_days = _longest_consecutive_day_run(valid_days)
    if longest_consecutive_valid_days < settings["minimum_valid_days_for_rhythm"]:
        qc_warnings.append(
            f"The longest run is {longest_consecutive_valid_days} consecutive valid day(s); multi-day rhythm "
            f"and SRI results require at least {settings['minimum_valid_days_for_rhythm']} consecutive valid "
            "days and will be unavailable."
        )

    payload = {
        "settings": settings,
        "recording_start": regular.index[0].isoformat(),
        "recording_end": regular.index[-1].isoformat(),
        "epoch_seconds": round(frequency.total_seconds(), 6),
        "calendar_days": len(daily_rows),
        "valid_days": len(valid_days),
        "longest_consecutive_valid_days": longest_consecutive_valid_days,
        "invalid_days": len(invalid_days),
        "completely_missing_days": len(completely_missing_days),
        "recording_gap_hours": gap_hours,
        "detected_nonwear_hours": detected_nonwear_hours,
        "manual_mask_hours": manual_mask_hours,
        "detected_nonwear_available": existing_mask is not None,
        "daily_qc": daily_rows,
        "warnings": qc_warnings,
    }

    analysis_raw._ui_source_activity_series = regular
    analysis_raw._ui_analysis_valid_mask = final_mask
    analysis_raw._ui_daily_qc = daily_rows
    analysis_raw._ui_valid_day_count = len(valid_days)
    analysis_raw._ui_longest_consecutive_valid_days = longest_consecutive_valid_days
    analysis_raw._ui_min_valid_days_for_rhythm = settings["minimum_valid_days_for_rhythm"]
    analysis_raw._ui_min_sleep_window_coverage = settings["minimum_sleep_window_coverage"]
    analysis_raw._ui_data_quality = payload
    return analysis_raw, payload

