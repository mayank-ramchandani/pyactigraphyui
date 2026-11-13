"""Streaming GGIR-*inspired* triaxial non-wear screening (not a GGIR port).

Uses native calibrated XYZ samples (in g), four consecutive 15-minute blocks
per 60-minute test, with minimum sample coverage, two qualifying axes and
no imputation of missing samples. GGIR has brand-specific thresholds and extra
post-processing; comparisons to GGIR QC remain essential.

Crespo and Roenneberg detect rest/sleep, NOT non-wear.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd

WINDOW_SECONDS = 3600
STEP_SECONDS = 900
DEFAULT_SD_G = 0.013
DEFAULT_RANGE_G = 0.050


@dataclass
class _Moments:
    n: int
    total: np.ndarray
    squared: np.ndarray
    minimum: np.ndarray
    maximum: np.ndarray


class TriaxialNonwear:
    """Bounded-memory sample-level summaries; requires known native rate in Hz.

    Conservative AND criterion per axis. This intentionally does not claim to
    replicate GGIR's post-processing or model-specific parameterization.
    """

    def __init__(self, sd_g=DEFAULT_SD_G, range_g=DEFAULT_RANGE_G, min_coverage=0.9,
                 approach="central", min_axes=2):
        if approach not in {"central", "full"}:
            raise ValueError("Non-wear approach must be central (GGIR 2013-like) or full (2023-like)")
        self.sd_g, self.range_g = float(sd_g), float(range_g)
        self.min_coverage = float(min_coverage)
        self.approach = approach
        self.min_axes = int(min_axes)
        self.blocks: dict[int, _Moments] = {}
        self.sample_rates: list[float] = []
        self.n_samples = 0

    def add(self, xyz: np.ndarray, start_seconds: float, sample_rate_hz: float) -> None:
        xyz = np.asarray(xyz, dtype=np.float64)
        rate = float(sample_rate_hz)
        if xyz.ndim != 2 or xyz.shape[1] != 3 or rate <= 0 or not len(xyz):
            return
        finite = np.all(np.isfinite(xyz), axis=1)
        secs = start_seconds + np.arange(len(xyz), dtype=np.float64) / rate
        buckets = np.floor(secs / STEP_SECONDS).astype(np.int64)
        for key in np.unique(buckets[finite]):
            part = xyz[(buckets == key) & finite]
            if not len(part):
                continue
            old = self.blocks.get(int(key))
            total = np.sum(part, axis=0)
            squared = np.sum(part * part, axis=0)
            minimum = np.min(part, axis=0)
            maximum = np.max(part, axis=0)
            if old:
                old.n += len(part)
                old.total += total
                old.squared += squared
                old.minimum = np.minimum(old.minimum, minimum)
                old.maximum = np.maximum(old.maximum, maximum)
            else:
                self.blocks[int(key)] = _Moments(len(part), total, squared, minimum, maximum)
            self.n_samples += len(part)
        if not self.sample_rates or abs(self.sample_rates[-1] - rate) > 0.01:
            self.sample_rates.append(rate)

    def finish(self) -> dict[str, Any]:
        flags: set[int] = set()
        windows_checked = 0
        rate = float(np.median(self.sample_rates)) if self.sample_rates else None
        if rate:
            for key in sorted(self.blocks):
                pieces = [self.blocks.get(key + j) for j in range(4)]
                if any(p is None for p in pieces):
                    continue
                n = sum(p.n for p in pieces)
                if n < self.min_coverage * WINDOW_SECONDS * rate:
                    continue
                total = sum((p.total for p in pieces), np.zeros(3))
                squared = sum((p.squared for p in pieces), np.zeros(3))
                lo = np.minimum.reduce([p.minimum for p in pieces])
                hi = np.maximum.reduce([p.maximum for p in pieces])
                sd = np.sqrt(np.maximum(squared / n - (total / n) ** 2, 0))
                windows_checked += 1
                if np.count_nonzero((sd < self.sd_g) & ((hi - lo) < self.range_g)) >= self.min_axes:
                    # Central 15m block or entire 60m; require measured coverage.
                    for candidate in ([key + 1] if self.approach == "central" else [key, key+1, key+2, key+3]):
                        flags.add(candidate)
        intervals = [
            {"start": pd.Timestamp(int(key * STEP_SECONDS), unit="s").isoformat(),
             "stop": pd.Timestamp(int((key + 1) * STEP_SECONDS), unit="s").isoformat()}
            for key in sorted(flags)
        ]
        return {"method": "triaxial_sd_range_60m_15m_ggir_inspired", "approach": self.approach,
                "sd_threshold_g": self.sd_g, "range_threshold_g": self.range_g,
                "min_axes": self.min_axes, "minimum_coverage": self.min_coverage,
                "native_sample_rate_hz": rate, "windows_checked": windows_checked,
                "native_samples_screened": self.n_samples, "nonwear_intervals": intervals,
                "limitations": "Approximation, not GGIR-identical: no GGIR brand calibration, "
                               "surrounded-wear rule, epoch imputation or full 2013/2023 refinements."}


def wear_mask_from_intervals(index: pd.DatetimeIndex, intervals: list[dict]) -> pd.Series:
    """Convert half-open non-wear intervals to an epoch mask without filling gaps."""
    valid = np.ones(len(index), dtype=bool)
    for pair in intervals:
        start, stop = pd.Timestamp(pair["start"]), pd.Timestamp(pair["stop"])
        # Timestamp conversions must match the source reader's timezone.
        if index.tz is not None and start.tzinfo is None:
            start, stop = start.tz_localize(index.tz), stop.tz_localize(index.tz)
        if index.tz is None and start.tzinfo is not None:
            start, stop = start.tz_localize(None), stop.tz_localize(None)
        valid &= ~((index >= start) & (index < stop))
    return pd.Series(valid, index=index, dtype=bool)
