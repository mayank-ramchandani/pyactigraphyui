import unittest

import numpy as np
import pandas as pd

from backend.activity_mapping import normalize_activity_mapping
from backend.accelerometer_loader import looks_like_accelerometer_timeseries_df
from backend.activity_metrics import (
    EpochPIMAccumulator,
    EpochTATAccumulator,
    EpochZCMAccumulator,
    StreamingMoments,
)


class ActivityMetricReducerTests(unittest.TestCase):
    def test_pim_integrates_absolute_dynamic_acceleration_across_chunks(self):
        accumulator = EpochPIMAccumulator(epoch_seconds=2)
        accumulator.add(np.full(7, 10.0), start_seconds=0.0, sample_rate=10.0)
        accumulator.add(np.full(13, 10.0), start_seconds=0.7, sample_rate=10.0)
        series = accumulator.series().dropna()
        self.assertEqual(len(series), 1)
        self.assertAlmostEqual(float(series.iloc[0]), 20.0, places=9)
        self.assertEqual(series.name, "PIM_mg_s")

    def test_zcm_counts_sign_changes_and_resets_across_gaps(self):
        accumulator = EpochZCMAccumulator(epoch_seconds=2, threshold_mg=4)
        accumulator.add(np.asarray([0, 10, 0, 10], dtype=float), start_seconds=0.0, sample_rate=2.0)
        accumulator.add(np.asarray([10, 0], dtype=float), start_seconds=4.0, sample_rate=2.0)
        series = accumulator.series()
        self.assertEqual(float(series.loc[series.index[0]]), 3.0)
        # The first sample after the gap does not create a crossing; only the
        # second sample in the new segment crosses.
        self.assertEqual(float(series.loc[series.index[-1]]), 1.0)
        self.assertEqual(accumulator.resets, 1)

    def test_tat_reports_seconds_above_threshold(self):
        accumulator = EpochTATAccumulator(epoch_seconds=2, threshold_mg=4)
        accumulator.add(np.asarray([0, 5, 10, 0], dtype=float), start_seconds=0.0, sample_rate=2.0)
        series = accumulator.series()
        self.assertAlmostEqual(float(series.iloc[0]), 1.0, places=9)
        self.assertEqual(series.name, "TAT_seconds")

    def test_streaming_moments_matches_recording_standard_deviation(self):
        moments = StreamingMoments()
        moments.add(np.asarray([0.0, 1.0]))
        moments.add(np.asarray([2.0, 3.0]))
        self.assertAlmostEqual(moments.standard_deviation(), float(np.std([0, 1, 2, 3])), places=12)

    def test_mapping_aliases_cover_pim_and_zcm(self):
        self.assertEqual(normalize_activity_mapping("proportional_integrating_mode"), "pim")
        self.assertEqual(normalize_activity_mapping("zero_crossings"), "zcm")
        self.assertEqual(normalize_activity_mapping("time_above_threshold"), "tat")

    def test_preprocessed_pim_and_zcm_aliases_are_detected(self):
        pim = pd.DataFrame({"time": ["2026-01-01"], "PIM_mg_s": [12.0]})
        zcm = pd.DataFrame({"time": ["2026-01-01"], "zeroCrossingMode": [4.0]})
        tat = pd.DataFrame({"time": ["2026-01-01"], "TAT_seconds": [2.0]})
        self.assertTrue(looks_like_accelerometer_timeseries_df(pim))
        self.assertTrue(looks_like_accelerometer_timeseries_df(zcm))
        self.assertTrue(looks_like_accelerometer_timeseries_df(tat))


if __name__ == "__main__":
    unittest.main()
