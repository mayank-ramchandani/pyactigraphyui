"""Streaming epoch reducers for raw acceleration-derived activity mappings.

The reducers operate on calibrated vector magnitude after optional filtering.
They retain only epoch totals, so memory use scales with the number of output
rows rather than the raw sample count.
"""

from __future__ import annotations

import os
from typing import Dict, Optional

import numpy as np
import pandas as pd


DEFAULT_ZCM_THRESHOLD_MG = float(os.getenv("ACTIVITY_ZCM_THRESHOLD_MG", "4"))


def _regular_epoch_series(keys, values, epoch_seconds: int, name: str) -> pd.Series:
    if not keys:
        return pd.Series(dtype=float, name=name)
    index = pd.to_datetime(np.asarray(keys, dtype=np.int64), unit="s")
    series = pd.Series(np.asarray(values, dtype=float), index=index, name=name).sort_index()
    full_index = pd.date_range(series.index.min(), series.index.max(), freq=f"{int(epoch_seconds)}s")
    return series.reindex(full_index)


class EpochPIMAccumulator:
    """Integrate absolute dynamic acceleration within each epoch.

    Input values are signed dynamic vector magnitude in mg (VM - 1 g). The
    resulting PIM is the area under ``abs(dynamic acceleration)`` and is
    reported in mg·s per epoch.
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
        weighted = np.abs(values) / float(sample_rate)
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
    """Count dead-band zero crossings of dynamic acceleration per epoch.

    Values within ``±threshold_mg`` are treated as a neutral zone. A crossing
    is counted when the last non-neutral sign changes. Continuity is reset when
    a timestamp gap is detected, preventing artificial crossings across missing
    recording periods.
    """

    def __init__(self, epoch_seconds: int, threshold_mg: float = DEFAULT_ZCM_THRESHOLD_MG):
        self.epoch_seconds = int(epoch_seconds)
        self.threshold_mg = max(0.0, float(threshold_mg))
        self.counts: Dict[int, int] = {}
        self.last_sign: int = 0
        self.expected_next: Optional[float] = None
        self.resets = 0

    def add(self, dynamic_mg: np.ndarray, start_seconds: float, sample_rate: float) -> None:
        values = np.asarray(dynamic_mg, dtype=np.float64).reshape(-1)
        rate = float(sample_rate)
        if not len(values) or rate <= 0:
            return

        tolerance = max(1e-6, 0.51 / rate)
        if self.expected_next is not None and abs(float(start_seconds) - self.expected_next) > tolerance:
            self.last_sign = 0
            self.resets += 1

        signs = np.zeros(len(values), dtype=np.int8)
        signs[values > self.threshold_mg] = 1
        signs[values < -self.threshold_mg] = -1
        nonzero_indices = np.flatnonzero(signs)
        if len(nonzero_indices):
            nonzero_signs = signs[nonzero_indices]
            previous = np.empty_like(nonzero_signs)
            previous[0] = self.last_sign
            if len(nonzero_signs) > 1:
                previous[1:] = nonzero_signs[:-1]
            crossing_mask = (previous != 0) & (nonzero_signs != previous)
            crossing_indices = nonzero_indices[crossing_mask]
            if len(crossing_indices):
                crossing_times = float(start_seconds) + crossing_indices.astype(np.float64) / rate
                epochs = np.floor(crossing_times / self.epoch_seconds).astype(np.int64) * self.epoch_seconds
                unique, counts = np.unique(epochs, return_counts=True)
                for epoch, count in zip(unique, counts):
                    key = int(epoch)
                    self.counts[key] = self.counts.get(key, 0) + int(count)
            self.last_sign = int(nonzero_signs[-1])

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
