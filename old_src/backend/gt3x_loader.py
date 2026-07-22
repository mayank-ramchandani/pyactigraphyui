"""Bounded-memory ActiGraph GT3X loading.

``pygt3x.FileReader`` eagerly materializes every raw sample and creates several
whole-recording copies.  A multi-week recording can therefore require many
gigabytes even though the epoch-level series needed by pyActigraphy is small.

This module uses pygt3x's low-level event and payload readers instead.  Each
activity event is calibrated, reduced into the selected epoch-level activity
basis, and released immediately.  Memory consequently scales with the number
of output epochs rather than the number of raw samples.
"""

from __future__ import annotations

from collections import deque
import json
import logging
import os
from pathlib import Path
import re
from typing import Any, Dict, Optional, Tuple
from zipfile import BadZipFile, ZipFile
import zlib

import numpy as np
import pandas as pd

try:
    from scipy.signal import butter, lfilter, lfilter_zi, sosfilt, sosfilt_zi
except Exception:  # pragma: no cover - deployment dependency
    butter = lfilter = lfilter_zi = sosfilt = sosfilt_zi = None

from .activity_mapping import attach_mapping_metadata, mapping_metadata, normalize_activity_mapping

try:
    from .diagnostics import update_current_stage
except Exception:  # pragma: no cover - permits standalone loader use
    def update_current_stage(**_: Any) -> None:
        return None

try:
    from pyActigraphy.io import BaseRaw
except Exception:  # pragma: no cover - depends on deployment environment
    BaseRaw = None


logger = logging.getLogger(__name__)

DEFAULT_GT3X_EPOCH_PERIOD = int(
    os.environ.get("GT3X_EPOCH_PERIOD", os.environ.get("ACCELEROMETER_EPOCH_PERIOD", "30"))
)
DEFAULT_GT3X_SAMPLE_RATE = float(os.environ.get("GT3X_DEFAULT_SAMPLE_RATE", "30"))
DEFAULT_GT3X_ACTIVITY_MODE = os.environ.get("GT3X_ACTIVITY_MODE", "counts").strip().lower()
GT3X_PROGRESS_EVENT_INTERVAL = max(1, int(os.environ.get("GT3X_PROGRESS_EVENT_INTERVAL", "100000")))
GT3X_DEDUPE_WINDOW_SECONDS = max(0, int(os.environ.get("GT3X_DEDUPE_WINDOW_SECONDS", "300")))
GT3X_ISM_FILL_CHUNK_SECONDS = max(1, int(os.environ.get("GT3X_ISM_FILL_CHUNK_SECONDS", "300")))
GT3X_STREAM_CHUNK_SECONDS = max(1, int(os.environ.get("GT3X_STREAM_CHUNK_SECONDS", "300")))
GT3X_PREVIEW_RAW_ROWS = max(1, int(os.environ.get("GT3X_PREVIEW_RAW_ROWS", "5")))

_DOTNET_TO_UNIX_TICKS = 621355968000000000


class GT3XProcessingError(ValueError):
    """Raised when GT3X loading or bounded-memory conversion fails."""


def _require_pygt3x():
    try:
        from pygt3x import Types
        from pygt3x.activity_payload import (
            read_activity1_payload,
            read_activity2_payload,
            read_activity3_payload,
            read_temperature_payload,
        )
        from pygt3x.calibration import CalibrationV2Service
        from pygt3x.components import Info
        from pygt3x.reader import LogReader
    except Exception as exc:  # pragma: no cover - deployment dependency
        raise GT3XProcessingError(
            "Direct .gt3x loading requires pygt3x. Add `pygt3x==0.7.1` to the "
            "backend requirements and redeploy the server."
        ) from exc
    return {
        "Types": Types,
        "read_activity1_payload": read_activity1_payload,
        "read_activity2_payload": read_activity2_payload,
        "read_activity3_payload": read_activity3_payload,
        "read_temperature_payload": read_temperature_payload,
        "CalibrationV2Service": CalibrationV2Service,
        "Info": Info,
        "LogReader": LogReader,
    }


def _coerce_sample_rate(value: Any, fallback: float = DEFAULT_GT3X_SAMPLE_RATE) -> float:
    try:
        rate = float(value)
        return rate if rate > 0 else float(fallback)
    except Exception:
        return float(fallback)


def _timezone_offset_seconds(value: Any) -> int:
    """Parse GT3X fixed offsets such as ``-04:00:00``."""
    match = re.fullmatch(r"\s*([+-]?)(\d{1,2}):(\d{2})(?::(\d{2}))?\s*", str(value or ""))
    if not match:
        return 0
    sign = -1 if match.group(1) == "-" else 1
    hours, minutes, seconds = (int(match.group(2)), int(match.group(3)), int(match.group(4) or 0))
    return sign * (hours * 3600 + minutes * 60 + seconds)


def _dotnet_ticks_to_local_timestamp(ticks: Any, offset_seconds: int) -> Optional[pd.Timestamp]:
    try:
        ticks_value = int(ticks)
        if ticks_value <= 0:
            return None
        unix_seconds = (ticks_value - _DOTNET_TO_UNIX_TICKS) / 10_000_000.0
        return pd.to_datetime(unix_seconds + offset_seconds, unit="s")
    except Exception:
        return None


def _dotnet_ticks_to_unix_seconds(ticks: Any) -> Optional[float]:
    try:
        ticks_value = int(ticks)
        if ticks_value <= 0:
            return None
        return (ticks_value - _DOTNET_TO_UNIX_TICKS) / 10_000_000.0
    except Exception:
        return None


def _read_optional_json(zip_file: ZipFile, name: str) -> Optional[dict]:
    if name not in zip_file.namelist():
        return None
    try:
        with zip_file.open(name) as handle:
            value = json.load(handle)
        return value if isinstance(value, dict) else None
    except Exception:
        return None


def _metadata_from_info(info: Any, file_path: str) -> Dict[str, Any]:
    timezone = getattr(info, "timezone", None)
    offset_seconds = _timezone_offset_seconds(timezone)
    start = _dotnet_ticks_to_local_timestamp(getattr(info, "start_date", 0), offset_seconds)
    last = _dotnet_ticks_to_local_timestamp(getattr(info, "last_sample_time", 0), offset_seconds)
    return {
        "_source": "gt3x_pygt3x_streaming",
        "_source_file": Path(file_path).name,
        "_processing_engine": "pygt3x_low_level_streaming_epoch_aggregation",
        "_streaming_loader": True,
        "start_time": start.isoformat() if start is not None else None,
        "last_sample_time": last.isoformat() if last is not None else None,
        "sample_rate": float(_coerce_sample_rate(getattr(info, "sample_rate", None))),
        "serial_number": getattr(info, "serial_number", None),
        "device": getattr(info, "device_type", None),
        "firmware": getattr(info, "firmware", None),
        "timezone": timezone,
        "timezone_offset_seconds": int(offset_seconds),
        "acceleration_scale": getattr(info, "acceleration_scale", None),
        "acceleration_min": getattr(info, "acceleration_min", None),
        "acceleration_max": getattr(info, "acceleration_max", None),
        "unexpected_resets": getattr(info, "unexpected_resets", None),
        "idle_sleep_mode_activated": None,
    }


class _Calibrator:
    def __init__(self, info: Any, calibration: Optional[dict], service_type: Any):
        self.info = info
        self.calibration = calibration
        self.service = None
        self.method = "device_scale"
        if (
            calibration is not None
            and "isCalibrated" in calibration
            and not bool(calibration.get("isCalibrated"))
        ):
            if int(calibration.get("calibrationMethod", -1)) != 2:
                raise GT3XProcessingError(
                    f"Unsupported GT3X calibration method: {calibration.get('calibrationMethod')}"
                )
            self.service = service_type(calibration, int(round(_coerce_sample_rate(info.sample_rate))))
            self.method = "pygt3x_calibration_v2"

    def apply(self, axes: np.ndarray) -> np.ndarray:
        values = np.asarray(axes, dtype=np.float64)
        if self.service is not None:
            return np.asarray(self.service.calibrate_samples(values), dtype=np.float32)
        scale = float(getattr(self.info, "acceleration_scale", 0) or 0)
        if not np.isfinite(scale) or scale <= 0:
            raise GT3XProcessingError("The GT3X metadata does not contain a valid acceleration scale.")
        return np.asarray(values / scale, dtype=np.float32)


class _EpochMeanAccumulator:
    def __init__(self, epoch_seconds: int, name: str):
        self.epoch_seconds = int(epoch_seconds)
        self.name = name
        self.sums: Dict[int, float] = {}
        self.counts: Dict[int, int] = {}

    def add(self, values: np.ndarray, start_seconds: float, sample_rate: float) -> None:
        values = np.asarray(values, dtype=np.float64).reshape(-1)
        if not len(values):
            return
        sample_times = start_seconds + np.arange(len(values), dtype=np.float64) / sample_rate
        epochs = np.floor(sample_times / self.epoch_seconds).astype(np.int64) * self.epoch_seconds
        for epoch in np.unique(epochs):
            selected = values[epochs == epoch]
            key = int(epoch)
            self.sums[key] = self.sums.get(key, 0.0) + float(np.sum(selected))
            self.counts[key] = self.counts.get(key, 0) + int(len(selected))

    def series(self) -> pd.Series:
        keys = sorted(self.sums)
        values = [self.sums[key] / self.counts[key] for key in keys if self.counts.get(key, 0)]
        keys = [key for key in keys if self.counts.get(key, 0)]
        return _regular_epoch_series(keys, values, self.epoch_seconds, self.name)


class _MadAccumulator:
    """Compute exact per-epoch MAD while retaining only a few recent epochs."""

    def __init__(self, epoch_seconds: int):
        self.epoch_seconds = int(epoch_seconds)
        self.pending: Dict[int, list[np.ndarray]] = {}
        self.results: Dict[int, float] = {}
        self.max_epoch: Optional[int] = None
        self.late_samples_skipped = 0

    def _finalize(self, key: int) -> None:
        chunks = self.pending.pop(key, [])
        if not chunks:
            return
        values = np.concatenate(chunks).astype(np.float64, copy=False)
        self.results[key] = float(np.mean(np.abs(values - values.mean())) * 1000.0)

    def add(self, values: np.ndarray, start_seconds: float, sample_rate: float) -> None:
        values = np.asarray(values, dtype=np.float32).reshape(-1)
        if not len(values):
            return
        sample_times = start_seconds + np.arange(len(values), dtype=np.float64) / sample_rate
        epochs = np.floor(sample_times / self.epoch_seconds).astype(np.int64) * self.epoch_seconds
        for epoch in np.unique(epochs):
            key = int(epoch)
            selected = values[epochs == epoch].copy()
            if key in self.results:
                self.late_samples_skipped += int(len(selected))
                continue
            self.pending.setdefault(key, []).append(selected)
            self.max_epoch = key if self.max_epoch is None else max(self.max_epoch, key)
        if self.max_epoch is not None:
            cutoff = self.max_epoch - 2 * self.epoch_seconds
            for key in sorted(item for item in self.pending if item < cutoff):
                self._finalize(key)

    def series(self) -> pd.Series:
        for key in sorted(list(self.pending)):
            self._finalize(key)
        keys = sorted(self.results)
        return _regular_epoch_series(
            keys, [self.results[key] for key in keys], self.epoch_seconds, "MAD_mg"
        )


class _StreamingVmLowPass:
    def __init__(self, sample_rate: float):
        self.enabled = bool(
            butter is not None
            and sosfilt is not None
            and sosfilt_zi is not None
            and float(sample_rate) > 40.0
        )
        self.sample_rate = float(sample_rate)
        self.sos = (
            butter(4, 20.0, btype="lowpass", fs=self.sample_rate, output="sos")
            if self.enabled
            else None
        )
        self.state = None
        self.expected_next: Optional[float] = None
        self.resets = 0

    def apply(self, values: np.ndarray, start_seconds: float) -> np.ndarray:
        values = np.asarray(values, dtype=np.float64)
        if not self.enabled or not len(values):
            return values
        tolerance = max(1e-6, 0.51 / self.sample_rate)
        if self.expected_next is not None and abs(start_seconds - self.expected_next) > tolerance:
            self.state = None
            self.resets += 1
        if self.state is None:
            self.state = sosfilt_zi(self.sos) * float(values[0])
        filtered, self.state = sosfilt(self.sos, values, zi=self.state)
        self.expected_next = start_seconds + len(values) / self.sample_rate
        return filtered


class _StreamingCounts30:
    """Streaming equivalent of agcounts' fast 30 Hz pipeline."""

    def __init__(self, epoch_seconds: int, sample_rate: float):
        if int(round(sample_rate)) != 30 or abs(float(sample_rate) - 30.0) > 1e-6:
            raise GT3XProcessingError(
                "Bounded-memory ActiGraph counts currently require a 30 Hz GT3X recording."
            )
        if lfilter is None or lfilter_zi is None:
            raise GT3XProcessingError("SciPy is required for bounded-memory ActiGraph counts.")
        try:
            from agcounts.legacy import INPUT_COEFFICIENTS, OUTPUT_COEFFICIENTS
        except Exception as exc:
            raise GT3XProcessingError(
                "ActiLife-style counts require `agcounts==0.2.6`."
            ) from exc
        self.b = np.asarray(INPUT_COEFFICIENTS[0, :], dtype=np.float64)
        self.a = np.asarray(OUTPUT_COEFFICIENTS[0, :], dtype=np.float64)
        self.epoch_seconds = int(epoch_seconds)
        self.sample_rate = 30.0
        self.state = None
        self.remainder = np.empty((3, 0), dtype=np.float64)
        self.expected_next: Optional[float] = None
        self.axis_sums: Dict[int, np.ndarray] = {}
        self.resets = 0

    def _reset(self) -> None:
        self.state = None
        self.remainder = np.empty((3, 0), dtype=np.float64)
        self.resets += 1

    def add(self, axes: np.ndarray, start_seconds: float) -> None:
        axes = np.asarray(axes, dtype=np.float64)
        if axes.ndim != 2 or axes.shape[1] != 3 or not len(axes):
            return
        tolerance = 0.51 / self.sample_rate
        if self.expected_next is not None and abs(start_seconds - self.expected_next) > tolerance:
            self._reset()

        data = np.round(axes.T, decimals=3)
        if self.state is None:
            zi = lfilter_zi(self.b, self.a).reshape((1, -1))
            self.state = zi.repeat(3, axis=0) * data[:, 0].reshape((-1, 1))
        filtered, self.state = lfilter(self.b, self.a, data, zi=self.state)
        filtered *= (3.0 / 4096.0) / (2.6 / 256.0) * 237.5
        trimmed = np.abs(filtered)
        trimmed[trimmed < 4] = 0
        trimmed[trimmed > 128] = 128
        trimmed = np.floor(trimmed)

        prior_remainder = self.remainder.shape[1]
        if prior_remainder:
            trimmed = np.concatenate((self.remainder, trimmed), axis=1)
        complete = (trimmed.shape[1] // 3) * 3
        self.remainder = trimmed[:, complete:].copy()
        if complete:
            grouped = np.floor(trimmed[:, :complete].reshape(3, -1, 3).sum(axis=2) / 3.0)
            first_group_offset = -prior_remainder / self.sample_rate
            group_times = (
                start_seconds
                + first_group_offset
                + np.arange(grouped.shape[1], dtype=np.float64) * (3.0 / self.sample_rate)
            )
            epochs = np.floor(group_times / self.epoch_seconds).astype(np.int64) * self.epoch_seconds
            for epoch in np.unique(epochs):
                key = int(epoch)
                contribution = grouped[:, epochs == epoch].sum(axis=1)
                if key in self.axis_sums:
                    self.axis_sums[key] += contribution
                else:
                    self.axis_sums[key] = contribution.astype(np.float64, copy=True)
        self.expected_next = start_seconds + len(axes) / self.sample_rate

    def series(self) -> pd.Series:
        keys = sorted(self.axis_sums)
        values = [float(np.sqrt(np.square(self.axis_sums[key]).sum())) for key in keys]
        return _regular_epoch_series(keys, values, self.epoch_seconds, "activity_counts_vm")


def _regular_epoch_series(
    epoch_keys: list[int], values: list[float], epoch_seconds: int, name: str
) -> pd.Series:
    if not epoch_keys:
        return pd.Series(dtype=float, name=name)
    index = pd.to_datetime(np.asarray(epoch_keys, dtype=np.int64), unit="s")
    series = pd.Series(np.asarray(values, dtype=float), index=index, name=name).sort_index()
    series = series[~series.index.duplicated(keep="last")]
    complete_index = pd.date_range(
        start=series.index[0], end=series.index[-1], freq=pd.to_timedelta(epoch_seconds, unit="s")
    )
    return series.reindex(complete_index)


def _decode_axes(event: Any, event_type: Any, sample_rate: float, api: dict) -> np.ndarray:
    if event_type == api["Types"].Activity:
        payload = api["read_activity1_payload"](event.payload, event.header.timestamp, sample_rate)
    elif event_type == api["Types"].Activity2:
        payload = api["read_activity2_payload"](event.payload, event.header.timestamp, sample_rate)
    elif event_type == api["Types"].Activity3:
        payload = api["read_activity3_payload"](event.payload, event.header.timestamp, sample_rate)
    else:
        return np.empty((0, 3), dtype=np.float32)
    if payload is None or not len(payload):
        return np.empty((0, 3), dtype=np.float32)
    return np.asarray(payload[:, 1:4], dtype=np.float32)


def _resolve_mode(
    requested_mapping: str, activity_mode: str, sample_rate: float
) -> Tuple[str, str, Optional[str]]:
    if requested_mapping in {"auto", "accelerometer"}:
        return "accelerometer", "accelerometer", None
    if requested_mapping == "mad":
        return "mad", "mad", None
    if requested_mapping == "enmo":
        return "enmo", "enmo", None

    mode = (activity_mode or "counts").strip().lower()
    if mode in {"enmo", "enmo_mg"}:
        return "enmo", "enmo", None
    if mode in {"mad", "mad_mg"}:
        return "mad", "mad", None
    if mode in {"accelerometer", "accelerometer_acc", "acc"}:
        return "accelerometer", "accelerometer", None
    if mode != "counts":
        raise GT3XProcessingError(f"Unsupported GT3X activity mode/mapping: {mode}")

    if abs(float(sample_rate) - 30.0) > 1e-6:
        reason = (
            f"Streaming ActiGraph counts are currently implemented for 30 Hz files; "
            f"this file reports {sample_rate:g} Hz. Processed acceleration was used instead."
        )
        return "accelerometer", "accelerometer", reason
    return "counts", "original", None


def _stream_gt3x_activity(
    file_path: str,
    epoch_period: int,
    activity_mode: str,
    activity_mapping: str,
) -> Tuple[pd.Series, Dict[str, Any], pd.DataFrame]:
    api = _require_pygt3x()
    source = Path(file_path)
    if not source.exists():
        raise GT3XProcessingError(f"GT3X input file does not exist: {source}")
    if int(epoch_period) <= 0:
        raise GT3XProcessingError("GT3X epoch period must be greater than zero seconds.")

    try:
        zip_file = ZipFile(source)
    except (BadZipFile, OSError) as exc:
        raise GT3XProcessingError(
            "Could not open this GT3X archive. Confirm the upload is complete and not corrupted."
        ) from exc

    with zip_file:
        names = set(zip_file.namelist())
        if "log.bin" not in names:
            raise GT3XProcessingError(
                "This appears to be a legacy GT3X archive without log.bin. The bounded-memory "
                "web loader currently supports log.bin GT3X recordings; export this file as "
                "epoch-count CSV/AGD or convert it locally."
            )
        try:
            info = api["Info"].read_zip(zip_file)
        except Exception as exc:
            raise GT3XProcessingError(f"Could not parse GT3X info.txt metadata: {exc}") from exc

        metadata = _metadata_from_info(info, file_path)
        sample_rate = _coerce_sample_rate(getattr(info, "sample_rate", None))
        timezone_offset = int(metadata["timezone_offset_seconds"])
        requested_mapping = normalize_activity_mapping(activity_mapping)
        mode, resolved_mapping, fallback_reason = _resolve_mode(
            requested_mapping, activity_mode, sample_rate
        )
        calibration = _read_optional_json(zip_file, "calibration.json")
        calibrator = _Calibrator(info, calibration, api["CalibrationV2Service"])

        counts_accumulator = None
        mean_accumulator = None
        mad_accumulator = None
        vm_filter = _StreamingVmLowPass(sample_rate)
        if mode == "counts":
            try:
                counts_accumulator = _StreamingCounts30(epoch_period, sample_rate)
            except GT3XProcessingError as exc:
                mode = "accelerometer"
                resolved_mapping = "accelerometer"
                fallback_reason = str(exc)
        if mode == "mad":
            mad_accumulator = _MadAccumulator(epoch_period)
        elif mode != "counts":
            name = "ACC_mg" if mode == "accelerometer" else "ENMO_mg"
            mean_accumulator = _EpochMeanAccumulator(epoch_period, name)

        raw_rows = 0
        event_count = 0
        activity_events = 0
        temperature_rows = 0
        checksum_failures = 0
        unsupported_events = 0
        duplicate_events = 0
        invalid_timestamp_events = 0
        idle_fill_samples = 0
        largest_event_samples = 0
        largest_chunk_samples = 0
        first_rows: list[dict[str, Any]] = []
        validation_vm: list[np.ndarray] = []
        validation_count = 0
        last_axes: Optional[np.ndarray] = None
        idle_start: Optional[int] = None
        last_event_timestamp: Optional[int] = None
        recent_keys: set[tuple[int, int, int, int]] = set()
        recent_queue: deque[tuple[int, tuple[int, int, int, int]]] = deque()
        max_timestamp_seen = -1
        recording_start_unix = _dotnet_ticks_to_unix_seconds(getattr(info, "start_date", 0))
        recording_end_unix = _dotnet_ticks_to_unix_seconds(getattr(info, "last_sample_time", 0))
        timestamp_tolerance = max(float(epoch_period), 300.0)

        def timestamp_is_plausible(value: int) -> bool:
            if recording_start_unix is not None and value < recording_start_unix - timestamp_tolerance:
                return False
            if recording_end_unix is not None and value > recording_end_unix + timestamp_tolerance:
                return False
            return True

        def process_axes(axes: np.ndarray, unix_start: float, idle_sleep: bool = False) -> None:
            nonlocal raw_rows, largest_chunk_samples, validation_count
            if axes is None or not len(axes):
                return
            calibrated = calibrator.apply(axes)
            raw_rows += int(len(calibrated))
            largest_chunk_samples = max(largest_chunk_samples, int(len(calibrated)))
            local_start = float(unix_start) + timezone_offset

            if validation_count < 100_000:
                take = min(len(calibrated), 100_000 - validation_count)
                sample = calibrated[:take].astype(np.float64, copy=False)
                validation_vm.append(np.sqrt(np.einsum("ij,ij->i", sample, sample)))
                validation_count += int(take)

            if len(first_rows) < GT3X_PREVIEW_RAW_ROWS:
                needed = GT3X_PREVIEW_RAW_ROWS - len(first_rows)
                for index, row in enumerate(calibrated[:needed]):
                    timestamp = pd.to_datetime(local_start + index / sample_rate, unit="s")
                    first_rows.append(
                        {
                            "Timestamp": timestamp.isoformat(),
                            "X": float(row[0]),
                            "Y": float(row[1]),
                            "Z": float(row[2]),
                            "IdleSleepMode": bool(idle_sleep),
                        }
                    )

            if counts_accumulator is not None and mode == "counts":
                counts_accumulator.add(calibrated, local_start)
                return

            vm = np.sqrt(np.einsum("ij,ij->i", calibrated, calibrated))
            if mad_accumulator is not None and mode == "mad":
                mad_accumulator.add(vm, local_start, sample_rate)
                return
            if mode == "accelerometer":
                vm = vm_filter.apply(vm, local_start)
            values = np.maximum(vm - 1.0, 0.0) * 1000.0
            assert mean_accumulator is not None
            mean_accumulator.add(values, local_start, sample_rate)

        pending_axes: list[np.ndarray] = []
        pending_start: Optional[float] = None
        pending_samples = 0
        pending_idle_sleep = False
        stream_chunk_samples = max(1, int(round(GT3X_STREAM_CHUNK_SECONDS * sample_rate)))

        def flush_pending_axes() -> None:
            nonlocal pending_axes, pending_start, pending_samples
            if not pending_axes or pending_start is None:
                return
            combined = np.concatenate(pending_axes, axis=0)
            process_axes(combined, pending_start, idle_sleep=pending_idle_sleep)
            pending_axes = []
            pending_start = None
            pending_samples = 0

        def queue_axes(axes: np.ndarray, unix_start: float, idle_sleep: bool = False) -> None:
            nonlocal pending_start, pending_samples, pending_idle_sleep
            if axes is None or not len(axes):
                return
            tolerance = max(1e-6, 0.51 / sample_rate)
            expected = (
                pending_start + pending_samples / sample_rate
                if pending_start is not None
                else None
            )
            if pending_axes and (
                expected is None
                or abs(float(unix_start) - expected) > tolerance
                or bool(idle_sleep) != pending_idle_sleep
            ):
                flush_pending_axes()
            if pending_start is None:
                pending_start = float(unix_start)
                pending_idle_sleep = bool(idle_sleep)
            pending_axes.append(np.asarray(axes, dtype=np.float32))
            pending_samples += int(len(axes))
            if pending_samples >= stream_chunk_samples:
                flush_pending_axes()

        def fill_idle_sleep(start_second: int, stop_second: int) -> None:
            nonlocal idle_fill_samples
            if last_axes is None or stop_second <= start_second:
                return
            seconds = int(stop_second - start_second)
            for offset in range(0, seconds, GT3X_ISM_FILL_CHUNK_SECONDS):
                chunk_seconds = min(GT3X_ISM_FILL_CHUNK_SECONDS, seconds - offset)
                sample_count = int(round(chunk_seconds * sample_rate))
                repeated = np.repeat(last_axes.reshape(1, 3), sample_count, axis=0)
                queue_axes(repeated, start_second + offset, idle_sleep=True)
                idle_fill_samples += sample_count

        log_info = zip_file.getinfo("log.bin")
        with zip_file.open("log.bin", "r") as log_handle:
            reader = api["LogReader"](log_handle)
            while True:
                event = reader.read_event()
                if event is None:
                    break
                event_count += 1
                event_timestamp = int(event.header.timestamp)

                if event_count % GT3X_PROGRESS_EVENT_INTERVAL == 0:
                    update_current_stage(
                        gt3x_streaming=True,
                        gt3x_events_read=event_count,
                        gt3x_raw_samples_reduced=raw_rows,
                        gt3x_log_progress_percent=round(
                            min(100.0, 100.0 * float(log_handle.tell()) / max(1, log_info.file_size)), 1
                        ),
                    )

                if not event.is_checksum_valid:
                    checksum_failures += 1
                    continue
                try:
                    event_type = api["Types"](event.header.event_type)
                except ValueError:
                    unsupported_events += 1
                    continue
                plausible_timestamp = timestamp_is_plausible(event_timestamp)
                if plausible_timestamp:
                    last_event_timestamp = event_timestamp

                if event_type == api["Types"].Params:
                    params = np.frombuffer(event.payload, dtype="<u8")
                    for param in params:
                        address = np.frombuffer(param.tobytes(), dtype="<u1")
                        if len(address) >= 5 and address[2] == 0x02:
                            metadata["idle_sleep_mode_activated"] = bool(np.bitwise_and(address[4], 4) == 4)
                    continue

                if event_type == api["Types"].Event and event.payload == b"\x08":
                    if plausible_timestamp:
                        idle_start = event_timestamp
                    continue
                if event_type == api["Types"].Event and event.payload == b"\x09":
                    if idle_start is not None and plausible_timestamp:
                        fill_idle_sleep(idle_start, event_timestamp)
                    idle_start = None
                    continue

                if event_type == api["Types"].TemperatureRecord:
                    if not plausible_timestamp:
                        continue
                    try:
                        temperature_rows += int(
                            len(api["read_temperature_payload"](event.payload, event.header.timestamp))
                        )
                    except Exception:
                        pass
                    continue

                if event_type not in {
                    api["Types"].Activity,
                    api["Types"].Activity2,
                    api["Types"].Activity3,
                }:
                    continue
                if int(event.header.payload_size) <= 1:
                    continue
                if not plausible_timestamp:
                    invalid_timestamp_events += 1
                    continue
                max_timestamp_seen = max(max_timestamp_seen, event_timestamp)

                signature = (
                    event_timestamp,
                    int(event.header.event_type),
                    int(event.header.payload_size),
                    int(zlib.crc32(event.payload)),
                )
                cutoff = max_timestamp_seen - GT3X_DEDUPE_WINDOW_SECONDS
                while recent_queue and recent_queue[0][0] < cutoff:
                    _, old_key = recent_queue.popleft()
                    recent_keys.discard(old_key)
                if signature in recent_keys:
                    duplicate_events += 1
                    continue
                recent_keys.add(signature)
                recent_queue.append((event_timestamp, signature))

                try:
                    raw_axes = _decode_axes(event, event_type, sample_rate, api)
                except Exception as exc:
                    logger.warning(
                        "Skipping malformed GT3X activity payload at %s: %s",
                        event.header.timestamp,
                        exc,
                    )
                    continue
                if not len(raw_axes):
                    continue
                activity_events += 1
                largest_event_samples = max(largest_event_samples, int(len(raw_axes)))
                queue_axes(raw_axes, float(event.header.timestamp))
                last_axes = np.asarray(raw_axes[-1], dtype=np.float32)
                idle_start = None

            if idle_start is not None and last_event_timestamp is not None:
                fill_idle_sleep(idle_start, last_event_timestamp)
            flush_pending_axes()

    if validation_vm:
        validation = np.concatenate(validation_vm)
        q95 = float(np.quantile(validation, 0.95))
        if not np.isfinite(q95) or q95 >= 16:
            raise GT3XProcessingError(
                "The decoded GT3X axes do not look like calibrated g units "
                f"(sampled vector-magnitude 95th percentile: {q95:.3g})."
            )
    else:
        q95 = None

    if mode == "counts" and counts_accumulator is not None:
        activity = counts_accumulator.series()
        mode_meta: Dict[str, Any] = {
            "_gt3x_activity_mode": "counts",
            "_gt3x_counts_axes": ["Axis1", "Axis2", "Axis3"],
            "_activity_units": "counts",
            "_filter_state_resets": counts_accumulator.resets,
        }
    elif mode == "mad" and mad_accumulator is not None:
        activity = mad_accumulator.series()
        mode_meta = {
            "_gt3x_activity_mode": "mad",
            "_activity_units": "mg",
            "_late_mad_samples_skipped": mad_accumulator.late_samples_skipped,
        }
    else:
        assert mean_accumulator is not None
        activity = mean_accumulator.series()
        mode_meta = {
            "_gt3x_activity_mode": "accelerometer_acc" if mode == "accelerometer" else "enmo",
            "_activity_units": "mg",
            "_vector_magnitude_lowpass_hz": 20 if vm_filter.enabled and mode == "accelerometer" else None,
            "_vector_magnitude_filter_order": 4 if vm_filter.enabled and mode == "accelerometer" else None,
            "_filter_state_resets": vm_filter.resets,
            "_raw_resampled_to_100_hz": False,
        }

    activity = activity.astype(float).sort_index()
    if int(activity.notna().sum()) < 2:
        raise GT3XProcessingError("The GT3X conversion produced fewer than two valid activity epochs.")

    activity_mapping_metadata = mapping_metadata(
        requested_mapping,
        resolved_mapping,
        source="pygt3x_streaming_raw_axes",
        epoch_seconds=int(epoch_period),
        calibrated_axes=True,
        available_mappings=["auto", "accelerometer", "original", "mad", "enmo"],
        original_mode=activity_mode,
    )
    metadata.update(mode_meta)
    metadata.update(
        {
            "_activity_mapping": activity_mapping_metadata,
            "_epoch_period_seconds": int(epoch_period),
            "_sample_rate_hz": float(sample_rate),
            "_timestamp_column": "GT3X event timestamp",
            "_axis_columns": ["X", "Y", "Z"],
            "_raw_rows": int(raw_rows),
            "_raw_columns": ["Timestamp", "X", "Y", "Z", "IdleSleepMode"],
            "_events_read": int(event_count),
            "_activity_events": int(activity_events),
            "_temperature_rows": int(temperature_rows),
            "_checksum_failures": int(checksum_failures),
            "_unsupported_events": int(unsupported_events),
            "_duplicate_activity_events_skipped": int(duplicate_events),
            "_invalid_timestamp_activity_events_skipped": int(invalid_timestamp_events),
            "_idle_sleep_samples_filled": int(idle_fill_samples),
            "_largest_raw_event_samples": int(largest_event_samples),
            "_largest_buffered_raw_chunk_samples": int(largest_chunk_samples),
            "_validation_vm_q95_g": q95,
            "_calibration_method": calibrator.method,
            "_missing_epoch_rows": int(activity.isna().sum()),
            "temperature_rows": int(temperature_rows),
        }
    )
    if fallback_reason:
        metadata["_gt3x_counts_fallback_reason"] = fallback_reason
    update_current_stage(
        gt3x_streaming=True,
        gt3x_events_read=event_count,
        gt3x_raw_samples_reduced=raw_rows,
        gt3x_output_epochs=int(activity.notna().sum()),
        gt3x_log_progress_percent=100.0,
    )
    return activity, metadata, pd.DataFrame(first_rows)


def prepare_gt3x_activity_series(
    file_path: str,
    epoch_period: int = DEFAULT_GT3X_EPOCH_PERIOD,
    activity_mode: str = DEFAULT_GT3X_ACTIVITY_MODE,
    activity_mapping: str = "auto",
) -> Tuple[pd.Series, Dict[str, Any], pd.DataFrame]:
    """Stream a GT3X recording directly into an epoch-level activity series."""
    try:
        return _stream_gt3x_activity(
            file_path,
            epoch_period=int(epoch_period),
            activity_mode=activity_mode,
            activity_mapping=activity_mapping,
        )
    except GT3XProcessingError:
        raise
    except Exception as exc:
        raise GT3XProcessingError(
            "Could not stream this .gt3x file. Confirm it is a complete raw ActiGraph "
            f"GT3X archive. Original error: {exc}"
        ) from exc


def read_gt3x_dataframe(file_path: str) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """Return a bounded raw-row preview for backwards compatibility.

    This intentionally does not recreate the former whole-recording DataFrame.
    Full activity processing must use :func:`prepare_gt3x_activity_series`.
    """
    _, metadata, preview = prepare_gt3x_activity_series(file_path)
    metadata = {**metadata, "_dataframe_is_bounded_preview": True}
    return preview, metadata


def load_gt3x_as_baseraw(
    file_path: str,
    epoch_period: int = DEFAULT_GT3X_EPOCH_PERIOD,
    activity_mode: str = DEFAULT_GT3X_ACTIVITY_MODE,
    activity_mapping: str = "auto",
):
    if BaseRaw is None:
        raise GT3XProcessingError("pyActigraphy.io.BaseRaw is not available in this backend environment.")

    activity, metadata, _ = prepare_gt3x_activity_series(
        file_path,
        epoch_period=epoch_period,
        activity_mode=activity_mode,
        activity_mapping=activity_mapping,
    )
    raw = BaseRaw(
        name=Path(file_path).stem,
        uuid=str(metadata.get("serial_number") or Path(file_path).stem),
        format="ActiGraph GT3X (streaming pygt3x)",
        axial_mode=None,
        start_time=activity.index[0],
        period=activity.index[-1] - activity.index[0],
        frequency=pd.to_timedelta(epoch_period, unit="s"),
        data=activity,
        light=None,
    )
    raw._ui_gt3x_summary = metadata
    raw._ui_source_format = "gt3x_pygt3x_streaming"
    return attach_mapping_metadata(raw, metadata.get("_activity_mapping") or mapping_metadata(activity_mapping))


def summarize_gt3x_file(
    file_path: str,
    epoch_period: int = DEFAULT_GT3X_EPOCH_PERIOD,
    activity_mode: str = DEFAULT_GT3X_ACTIVITY_MODE,
    activity_mapping: str = "auto",
) -> Dict[str, Any]:
    activity, metadata, preview = prepare_gt3x_activity_series(
        file_path,
        epoch_period=epoch_period,
        activity_mode=activity_mode,
        activity_mapping=activity_mapping,
    )
    valid = activity.dropna()
    return {
        "rows": int(metadata.get("_raw_rows", 0)),
        "valid_activity_rows": int(len(valid)),
        "columns": list(metadata.get("_raw_columns", [])),
        "activity_column": str(activity.name),
        "start_time": activity.index[0].isoformat(),
        "end_time": activity.index[-1].isoformat(),
        "frequency": str(pd.to_timedelta(epoch_period, unit="s")),
        "activity_mean": float(valid.mean()),
        "activity_min": float(valid.min()),
        "activity_max": float(valid.max()),
        "activity_nonzero_fraction": float((valid > 0).mean()),
        "activity_mapping": metadata.get("_activity_mapping"),
        "light_available": False,
        "first_rows": preview.astype(str).to_dict(orient="records"),
        "gt3x_summary": metadata,
    }
