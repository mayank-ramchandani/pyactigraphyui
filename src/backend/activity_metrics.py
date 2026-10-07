"""Streaming epoch reducers for raw acceleration-derived activity mappings.

The reducers in this module intentionally receive *metric-specific* inputs.
PIM, ZCM, and TAT use unfiltered gravity-normalized vector magnitude
``abs(VM - 1 g)`` in milligravity units.  ENMO and MAD are calculated by their
dedicated loaders.  This keeps signal processing order explicit instead of
applying one global filter to every activity representation.
"""

from __future__ import annotations

import os
from typing import Dict, Optional

import numpy as np
import pandas as pd


DEFAULT_ZCM_THRESHOLD_MG = float(os.getenv("ACTIVITY_ZCM_THRESHOLD_MG", "4"))
DEFAULT_TAT_THRESHOLD_MG = float(os.getenv("ACTIVITY_TAT_THRESHOLD_MG", "150"))


class StreamingMoments:
    """Numerically stable streaming mean/variance for a complete recording."""

    def __init__(self):
        self.count = 0
        self.mean = 0.0
        self.m2 = 0.0

    def add(self, values: np.ndarray) -> None:
        clean = np.asarray(values, dtype=np.float64).reshape(-1)
        clean = clean[np.isfinite(clean)]
        if not len(clean):
            return
        chunk_count = int(len(clean))
        chunk_mean = float(np.mean(clean))
        chunk_m2 = float(np.sum(np.square(clean - chunk_mean)))
        if self.count == 0:
            self.count = chunk_count
            self.mean = chunk_mean
            self.m2 = chunk_m2
            return
        total = self.count + chunk_count
        delta = chunk_mean - self.mean
        self.m2 += chunk_m2 + (delta * delta) * self.count * chunk_count / total
        self.mean += delta * chunk_count / total
        self.count = total

    def standard_deviation(self) -> float:
        if self.count <= 0:
            return float("nan")
        return float(np.sqrt(max(0.0, self.m2 / self.count)))


def _regular_epoch_series(keys, values, epoch_seconds: int, name: str) -> pd.Series:
    if not keys:
        return pd.Series(dtype=float, name=name)
    index = pd.to_datetime(np.asarray(keys, dtype=np.int64), unit="s")
    series = pd.Series(np.asarray(values, dtype=float), index=index, name=name).sort_index()
    full_index = pd.date_range(series.index.min(), series.index.max(), freq=f"{int(epoch_seconds)}s")
    return series.reindex(full_index)


class EpochPIMAccumulator:
    """Integrate gravity-normalized vector magnitude within each epoch.

    Input values are ``abs(VM - 1 g)`` in mg.  The resulting PIM is the area
    under the normalized magnitude and is reported in mg·s per epoch.  The
    native sample interval is included so sampling rate alone does not inflate
    the result.
    """

    def __init__(self, epoch_seconds: int):
        self.epoch_seconds = int(epoch_seconds)
        self.totals: Dict[int, float] = {}
        self.sample_counts: Dict[int, int] = {}

    def add(self, dynamic_mg: np.ndarray, start_seconds: float, sample_rate: float) -> None:
        values = np.asarray(dynamic_mg, dtype=np.float64).reshape(-1)
        if not len(values) or float(sample_rate) <= 0:
            return
        sample_times = float(start_seconds) + np.arange(len(values), dtype=np.float64) / float(sample_rate)
        epochs = np.floor(sample_times / self.epoch_seconds).astype(np.int64) * self.epoch_seconds
        weighted = np.maximum(values, 0.0) / float(sample_rate)
        unique, inverse = np.unique(epochs, return_inverse=True)
        totals = np.bincount(inverse, weights=weighted)
        counts = np.bincount(inverse)
        for idx, epoch in enumerate(unique):
            key = int(epoch)
            self.totals[key] = self.totals.get(key, 0.0) + float(totals[idx])
            self.sample_counts[key] = self.sample_counts.get(key, 0) + int(counts[idx])

    def series(self) -> pd.Series:
        keys = sorted(self.totals)
        return _regular_epoch_series(
            keys,
            [self.totals[key] for key in keys],
            self.epoch_seconds,
            "PIM_mg_s",
        )


class EpochZCMAccumulator:
    """Count level crossings of normalized magnitude per epoch.

    ZCM is defined here as the number of transitions across one positive
    threshold in ``abs(VM - 1 g)``.  Continuity is reset when a timestamp gap is
    detected, preventing artificial crossings across missing periods.
    """

    def __init__(self, epoch_seconds: int, threshold_mg: float = DEFAULT_ZCM_THRESHOLD_MG):
        self.epoch_seconds = int(epoch_seconds)
        self.threshold_mg = max(0.0, float(threshold_mg))
        self.counts: Dict[int, int] = {}
        self.last_above: Optional[bool] = None
        self.expected_next: Optional[float] = None
        self.resets = 0

    def add(self, dynamic_mg: np.ndarray, start_seconds: float, sample_rate: float) -> None:
        values = np.asarray(dynamic_mg, dtype=np.float64).reshape(-1)
        rate = float(sample_rate)
        if not len(values) or rate <= 0:
            return

        tolerance = max(1e-6, 0.51 / rate)
        if self.expected_next is not None and abs(float(start_seconds) - self.expected_next) > tolerance:
            self.last_above = None
            self.resets += 1

        above = values > self.threshold_mg
        previous = np.empty_like(above)
        previous[0] = above[0] if self.last_above is None else self.last_above
        if len(above) > 1:
            previous[1:] = above[:-1]
        crossing_indices = np.flatnonzero(above != previous)
        if len(crossing_indices):
            crossing_times = float(start_seconds) + crossing_indices.astype(np.float64) / rate
            epochs = np.floor(crossing_times / self.epoch_seconds).astype(np.int64) * self.epoch_seconds
            unique, counts = np.unique(epochs, return_counts=True)
            for epoch, count in zip(unique, counts):
                key = int(epoch)
                self.counts[key] = self.counts.get(key, 0) + int(count)
        self.last_above = bool(above[-1])

        # Ensure epochs with samples but no crossings are represented as zero.
        sample_times = float(start_seconds) + np.array([0.0, (len(values) - 1) / rate])
        first_epoch = int(np.floor(sample_times[0] / self.epoch_seconds) * self.epoch_seconds)
        last_epoch = int(np.floor(sample_times[1] / self.epoch_seconds) * self.epoch_seconds)
        for epoch in range(first_epoch, last_epoch + self.epoch_seconds, self.epoch_seconds):
            self.counts.setdefault(epoch, 0)

        self.expected_next = float(start_seconds) + len(values) / rate

    def series(self) -> pd.Series:
        keys = sorted(self.counts)
        return _regular_epoch_series(
            keys,
            [self.counts[key] for key in keys],
            self.epoch_seconds,
            "ZCM_crossings",
        )


class EpochTATAccumulator:
    """Accumulate time above a positive normalized-magnitude threshold."""

    def __init__(self, epoch_seconds: int, threshold_mg: float = DEFAULT_TAT_THRESHOLD_MG):
        self.epoch_seconds = int(epoch_seconds)
        self.threshold_mg = max(0.0, float(threshold_mg))
        self.seconds: Dict[int, float] = {}

    def add(self, normalized_mg: np.ndarray, start_seconds: float, sample_rate: float) -> None:
        values = np.asarray(normalized_mg, dtype=np.float64).reshape(-1)
        rate = float(sample_rate)
        if not len(values) or rate <= 0:
            return
        sample_times = float(start_seconds) + np.arange(len(values), dtype=np.float64) / rate
        epochs = np.floor(sample_times / self.epoch_seconds).astype(np.int64) * self.epoch_seconds
        weights = (values > self.threshold_mg).astype(np.float64) / rate
        unique, inverse = np.unique(epochs, return_inverse=True)
        totals = np.bincount(inverse, weights=weights)
        for idx, epoch in enumerate(unique):
            key = int(epoch)
            self.seconds[key] = self.seconds.get(key, 0.0) + float(totals[idx])

    def series(self) -> pd.Series:
        keys = sorted(self.seconds)
        return _regular_epoch_series(
            keys,
            [self.seconds[key] for key in keys],
            self.epoch_seconds,
            "TAT_seconds",
        )
