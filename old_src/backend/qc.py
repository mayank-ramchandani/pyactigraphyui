"""Lightweight, non-fatal quality-control checks for analysis results.

These checks must never prevent otherwise valid metric results from being
returned. In particular, pyActigraphy periodic metrics may return NumPy arrays,
Pandas Series, lists, or scalars, so QC avoids direct comparisons such as
``value == []`` that can raise length-mismatch or ambiguous-truth errors.
"""

from __future__ import annotations

import math
from typing import Any


def _is_empty_collection(value: Any) -> bool:
    """Return True only when *value* is a collection with zero elements.

    ``len`` works safely for lists, tuples, dictionaries, NumPy arrays, and
    Pandas objects. Scalars and objects without a length are treated as
    non-empty. Strings are intentionally treated as collections so an empty
    string can be identified without comparing it to another sequence.
    """

    if value is None:
        return False
    try:
        return len(value) == 0
    except (TypeError, AttributeError):
        return False


def _finite_scalar(value: Any):
    """Convert a scalar-like value to float, or return None for arrays/objects."""

    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    return number if math.isfinite(number) else None


def _outside_range(value: Any, minimum: float, maximum: float) -> bool:
    number = _finite_scalar(value)
    return number is not None and not (minimum <= number <= maximum)


def quick_qc(metrics: dict):
    warnings = []

    sri = metrics.get("sri")
    if sri is not None and _outside_range(sri, 0, 100):
        warnings.append("SRI is outside the expected 0-100 range.")

    ra = metrics.get("ra")
    if ra is not None and _outside_range(ra, 0, 1):
        warnings.append("RA is outside the expected 0-1 range.")
    else:
        ra_number = _finite_scalar(ra)
        if ra_number is not None and abs(ra_number - 1.0) < 1e-12:
            warnings.append(
                "RA is exactly 1.000. This is mathematically possible when L5 is zero, "
                "but it can also indicate that binarization/thresholding made the least-active "
                "5-hour window entirely inactive. Inspect the RA stage diagnostics for M10, L5, "
                "threshold, and binarization settings; consider non-binarized RA for ENMO/MAD."
            )

    sleep_efficiency = metrics.get("sleep_efficiency")
    if sleep_efficiency is not None and _outside_range(sleep_efficiency, 0, 100):
        warnings.append("Sleep Efficiency is outside the expected 0-100 range.")

    if metrics.get("kra") is None and "kra" in metrics:
        warnings.append("kRA could not be computed with the current file or settings.")

    if metrics.get("kar") is None and "kar" in metrics:
        warnings.append("kAR could not be computed with the current file or settings.")

    for metric_id in ["isp", "ivp", "rap"]:
        if metric_id in metrics and _is_empty_collection(metrics.get(metric_id)):
            warnings.append(
                f"{metric_id.upper()} returned an empty collection; "
                "the recording may be too short for the selected period."
            )

    return warnings
