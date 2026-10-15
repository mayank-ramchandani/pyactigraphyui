"""Configurable, bounded-memory processing of calibrated *raw* triaxial acceleration.

This module deliberately produces epoch-ready sample values (internal mg).  It
never attempts to reconstruct X/Y/Z from activity counts or precomputed epochs.
See Maczák et al., PLOS ONE 2021, doi:10.1371/journal.pone.0261718.
"""
from __future__ import annotations

import math
from typing import Any

import numpy as np

try:
    from scipy.signal import butter, sosfilt, sosfilt_zi
except ImportError:  # explicit failure only when custom filtering is requested
    butter = sosfilt = sosfilt_zi = None

DEFAULT_RAW_SIGNAL = {
    "enabled": False,
    "filter_type": "none",       # none / lowpass / highpass / bandpass
    "filter_stage": "axes",      # axes / magnitude
    "filter_order": 3,
    "low_cutoff_hz": 0.25,        # bandpass lower / highpass cutoff
    "high_cutoff_hz": 2.5,        # bandpass upper / lowpass cutoff
    "normalization": "positive_deviation",  # none / absolute / subtract_one / absolute_deviation / positive_deviation
    "gravity_g": 1.0,
    "output_unit": "mg",        # mg / g / m_s2; applied AFTER epoch reduction
}


def normalize_raw_signal_settings(value: Any) -> dict:
    if value is None:
        value = {}
    if not isinstance(value, dict):
        raise ValueError("Raw acceleration preprocessing settings must be a JSON object.")
    result = {**DEFAULT_RAW_SIGNAL, **value}
    if not isinstance(result["enabled"], bool):
        raise ValueError("Raw acceleration preprocessing 'enabled' must be true or false.")
    choices = {
        "filter_type": {"none", "lowpass", "highpass", "bandpass"},
        "filter_stage": {"axes", "magnitude"},
        "normalization": {"none", "absolute", "subtract_one", "absolute_deviation", "positive_deviation"},
        "output_unit": {"mg", "g", "m_s2"},
    }
    for field, allowed in choices.items():
        if result[field] not in allowed:
            raise ValueError(f"Invalid {field}: {result[field]!r}. Choose one of {', '.join(sorted(allowed))}.")
    try:
        order = int(result["filter_order"])
        if str(result["filter_order"]) not in {str(order), str(float(order))}:
            raise ValueError()
        result["filter_order"] = order
        for name in ("low_cutoff_hz", "high_cutoff_hz", "gravity_g"):
            result[name] = float(result[name])
    except (ValueError, TypeError, OverflowError) as exc:
        raise ValueError("Filter order, cutoffs and gravity must be finite numeric values.") from exc
    if not 1 <= order <= 8:
        raise ValueError("Butterworth filter order must be between 1 and 8.")
    if any(not math.isfinite(result[name]) for name in ("low_cutoff_hz", "high_cutoff_hz", "gravity_g")):
        raise ValueError("Cutoff frequencies and gravity must be finite.")
    if not 0.1 <= result["gravity_g"] <= 2.0:
        raise ValueError("Gravity reference must be 0.1–2.0 g.")
    if result["filter_type"] != "none":
        if result["filter_type"] in {"highpass", "bandpass"} and result["low_cutoff_hz"] <= 0:
            raise ValueError("High-pass/lower cutoff must be greater than zero Hz.")
        if result["filter_type"] in {"lowpass", "bandpass"} and result["high_cutoff_hz"] <= 0:
            raise ValueError("Low-pass/upper cutoff must be greater than zero Hz.")
        if result["filter_type"] == "bandpass" and result["low_cutoff_hz"] >= result["high_cutoff_hz"]:
            raise ValueError("Band-pass lower cutoff must be less than upper cutoff.")
    if result["enabled"] and result["filter_type"] in {"highpass", "bandpass"} and result["normalization"] in {"subtract_one", "absolute_deviation", "positive_deviation"}:
        raise ValueError("High-pass/band-pass filtering removes the static gravity component. Choose 'No gravity subtraction' or 'Absolute amplitude' normalization instead of subtracting 1 g.")
    return result


def raw_signal_units(config: dict, metric: str) -> str:
    unit = {"mg": "mg", "g": "g", "m_s2": "m/s²"}[config["output_unit"]]
    if metric == "pim":
        return f"{unit}·s/epoch"
    if metric == "zcm":
        return "crossings/epoch"
    if metric == "tat":
        return "s/epoch"
    return unit


def output_unit_factor(config: dict) -> float:
    # Internal magnitude/metric values are always in mg until final aggregation.
    return {"mg": 1.0, "g": 0.001, "m_s2": 0.00980665}[config["output_unit"]]


class RawSignalProcessor:
    """Streaming causal Butterworth filter with continuity-aware state resets.

    Filtering is forward/causal: forward-backward zero-phase filtering cannot
    safely be performed online without materializing continuous recordings.
    """

    def __init__(self, settings: dict):
        self.settings = normalize_raw_signal_settings(settings)
        self.sample_rate = None
        self.expected_next = None
        self.sos = None
        self.zi = None
        self.resets = 0

    def _prepare(self, frequency: float, first_time: float, values: np.ndarray):
        config = self.settings
        new_segment = self.sample_rate is None or abs(self.sample_rate - frequency) > 1e-6
        if self.expected_next is not None and abs(first_time - self.expected_next) > max(0.51 / frequency, 1e-6):
            new_segment = True
        if not new_segment:
            return
        if self.sample_rate is not None:
            self.resets += 1
        self.sample_rate = frequency
        self.sos = None
        self.zi = None
        if config["filter_type"] == "none":
            return
        if butter is None or sosfilt is None or sosfilt_zi is None:
            raise ValueError("Custom raw filtering requires SciPy to be installed on the server.")
        nyquist = frequency / 2.0
        filter_type = config["filter_type"]
        low, high = config["low_cutoff_hz"], config["high_cutoff_hz"]
        chosen = high if filter_type == "lowpass" else low if filter_type == "highpass" else (low, high)
        largest = max(chosen) if isinstance(chosen, tuple) else chosen
        if largest >= nyquist:
            raise ValueError(f"Filter cutoff {largest:g} Hz must be less than the Nyquist frequency {nyquist:g} Hz (raw sampling rate {frequency:g} Hz).")
        self.sos = butter(config["filter_order"], chosen, btype=filter_type, fs=frequency, output="sos")
        initial = np.asarray(values[0], dtype=np.float64).reshape(-1)
        self.zi = sosfilt_zi(self.sos)[:, :, None] * initial[None, None, :]

    def apply(self, calibrated_axes_g: np.ndarray, start_seconds: float, sample_rate: float) -> np.ndarray:
        axes = np.asarray(calibrated_axes_g, dtype=np.float64)
        if axes.ndim != 2 or axes.shape[1] != 3:
            raise ValueError("Raw signal preprocessing requires calibrated N×3 X/Y/Z acceleration samples.")
        if not len(axes):
            return np.empty(0, dtype=np.float64)
        if not np.isfinite(axes).all():
            raise ValueError("Raw triaxial samples contain nonfinite acceleration values.")
        freq = float(sample_rate)
        if not math.isfinite(freq) or freq <= 0:
            raise ValueError("Raw sample rate must be a positive finite frequency.")
        stage = self.settings["filter_stage"]
        values = axes if stage == "axes" else np.linalg.norm(axes, axis=1).reshape(-1, 1)
        self._prepare(freq, float(start_seconds), values)
        if self.sos is not None:
            filtered, self.zi = sosfilt(self.sos, values, axis=0, zi=self.zi)
        else:
            filtered = values
        magnitude_g = np.linalg.norm(filtered, axis=1) if stage == "axes" else filtered[:, 0]
        normalization = self.settings["normalization"]
        if normalization == "absolute":
            magnitude_g = np.abs(magnitude_g)
        elif normalization != "none":
            magnitude_g = magnitude_g - self.settings["gravity_g"]
            if normalization == "absolute_deviation":
                magnitude_g = np.abs(magnitude_g)
            elif normalization == "positive_deviation":
                magnitude_g = np.maximum(magnitude_g, 0.0)
        self.expected_next = float(start_seconds) + len(axes) / freq
        return magnitude_g * 1000.0
