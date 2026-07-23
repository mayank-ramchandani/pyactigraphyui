import unittest
from unittest.mock import patch

import numpy as np
import pandas as pd

from backend.analysis import (
    _compute_waso_and_efficiency,
    _missing_aware_sri,
    _score_minutes_in_windows,
    compute_metric,
)
from backend.data_quality import apply_data_quality_control, resolve_data_quality_settings
from backend.geneactiv_bin import GeneActivRaw, SimpleLightRecording


class FakeRaw:
    def __init__(self, data, mask=None):
        self.data = data
        self.frequency = data.index.freq or pd.Timedelta("1min")
        self.format = "test"
        if mask is not None:
            self.mask = mask

    @property
    def raw_data(self):
        return self.data


class DataQualityTests(unittest.TestCase):
    def test_pyactigraphy_style_read_only_data_is_rebuilt_with_active_mask(self):
        class ReadOnlyRaw:
            def __init__(self, name, uuid, format, axial_mode, start_time, period, frequency, data, light, fpath=None):
                self.name = name
                self.uuid = uuid
                self.format = format
                self.axial_mode = axial_mode
                self.start_time = start_time
                self.period = period
                self.frequency = frequency
                self.raw_light = light
                self.fpath = fpath
                self._data = data
                self.mask = None
                self.mask_inactivity = False
                self.exclude_if_mask = True

            @property
            def raw_data(self):
                return self._data

            @property
            def data(self):
                if self.mask_inactivity and self.mask is not None:
                    return self._data.where(self.mask > 0)
                return self._data

        index = pd.date_range("2026-01-10", periods=24, freq="1h")
        source = ReadOnlyRaw("test", "uuid", "Pandas", None, index[0], index[-1] - index[0], pd.Timedelta("1h"), pd.Series(1.0, index=index), None)
        source._ui_mask_intervals = [{"start": "2026-01-10 04:00", "stop": "2026-01-10 05:00"}]

        with patch("backend.data_quality.BaseRaw", ReadOnlyRaw):
            cleaned, quality = apply_data_quality_control(source, {"masking": {"minimumValidHoursPerDay": 16}})

        self.assertIsInstance(cleaned, ReadOnlyRaw)
        self.assertTrue(cleaned.mask_inactivity)
        self.assertTrue(cleaned.exclude_if_mask)
        self.assertEqual(quality["valid_days"], 1)
        self.assertTrue(pd.isna(cleaned.data.loc["2026-01-10 04:00"]))
        self.assertEqual(float(cleaned.data.loc["2026-01-10 03:00"]), 1.0)

    def test_gaps_nonwear_manual_masks_and_invalid_days_are_separate(self):
        index = pd.date_range("2026-01-01", periods=3 * 24 * 60, freq="1min")
        activity = pd.Series(5.0, index=index, name="activity")
        # Day 2 has only 15 recorded hours and must fail the 16 h valid-day rule.
        activity.loc["2026-01-02 15:00":"2026-01-02 23:59"] = np.nan

        native_wear = pd.Series(1, index=index, dtype=int)
        native_wear.loc["2026-01-01 00:00":"2026-01-01 01:59"] = 0
        raw = FakeRaw(activity, mask=native_wear)
        raw._ui_mask_intervals = [{
            "start": "2026-01-03 10:00",
            "stop": "2026-01-03 10:59",
            "source": "test",
        }]

        cleaned, quality = apply_data_quality_control(raw, {
            "masking": {
                "respectNonwear": True,
                "minimumValidHoursPerDay": 16,
                "minimumValidDaysForRhythm": 2,
                "minimumSleepWindowCoverage": 0.8,
            }
        })

        self.assertEqual(quality["valid_days"], 2)
        self.assertEqual(quality["invalid_days"], 1)
        self.assertAlmostEqual(quality["daily_qc"][0]["detected_nonwear_hours"], 2.0)
        self.assertAlmostEqual(quality["daily_qc"][1]["recording_gap_hours"], 9.0)
        self.assertAlmostEqual(quality["daily_qc"][2]["manual_mask_hours"], 1.0)
        self.assertFalse(quality["daily_qc"][1]["valid_day"])
        self.assertTrue(cleaned.data.loc["2026-01-02"].isna().all())
        self.assertTrue(cleaned.data.loc["2026-01-01 00:30"] != 0 or pd.isna(cleaned.data.loc["2026-01-01 00:30"]))

    def test_completely_missing_day_remains_nan_and_is_reported(self):
        index = pd.date_range("2026-02-01", periods=3 * 24, freq="1h")
        activity = pd.Series(3.0, index=index)
        activity.loc["2026-02-02"] = np.nan
        cleaned, quality = apply_data_quality_control(FakeRaw(activity), {"masking": {}})

        self.assertEqual(quality["completely_missing_days"], 1)
        self.assertEqual(quality["daily_qc"][1]["recorded_hours"], 0.0)
        self.assertTrue(cleaned.data.loc["2026-02-02"].isna().all())

    def test_direct_bin_raw_uses_the_same_valid_day_pipeline(self):
        index = pd.date_range("2026-02-10", periods=3 * 24, freq="1h")
        activity = pd.Series(8.0, index=index, name="ACC_mg")
        activity.loc["2026-02-11"] = np.nan
        raw = GeneActivRaw(activity, SimpleLightRecording({}))

        cleaned, quality = apply_data_quality_control(raw, {
            "masking": {"minimumValidHoursPerDay": 16, "respectNonwear": True}
        })

        self.assertIsInstance(cleaned, GeneActivRaw)
        self.assertEqual(quality["completely_missing_days"], 1)
        self.assertEqual(quality["valid_days"], 2)
        self.assertTrue(cleaned.data.loc["2026-02-11"].isna().all())

    def test_respect_nonwear_can_be_disabled_without_disabling_manual_masks(self):
        index = pd.date_range("2026-03-01", periods=24, freq="1h")
        activity = pd.Series(2.0, index=index)
        native_wear = pd.Series(0, index=index)
        raw = FakeRaw(activity, mask=native_wear)
        raw._ui_mask_intervals = [{"start": "2026-03-01 10:00", "stop": "2026-03-01 11:00"}]

        cleaned, quality = apply_data_quality_control(raw, {
            "masking": {"respectNonwear": False, "minimumValidHoursPerDay": 16}
        })

        self.assertFalse(quality["detected_nonwear_available"])
        self.assertEqual(quality["valid_days"], 1)
        self.assertTrue(pd.isna(cleaned.data.loc["2026-03-01 10:00"]))
        self.assertEqual(float(cleaned.data.loc["2026-03-01 09:00"]), 2.0)

    def test_sleep_windows_below_coverage_threshold_are_unavailable(self):
        index = pd.date_range("2026-04-01 22:00", periods=8 * 60, freq="1min")
        score = pd.Series(1.0, index=index)
        score.iloc[:120] = np.nan  # 75% coverage
        windows = [{"start": index[0], "stop": index[0] + pd.Timedelta("8h")}]

        minutes, details = _score_minutes_in_windows(score, windows, minimum_coverage=0.80)
        summary = _compute_waso_and_efficiency(
            score, windows, window_quality=details, minimum_coverage=0.80
        )

        self.assertIsNone(minutes)
        self.assertFalse(details[0]["eligible"])
        self.assertAlmostEqual(details[0]["coverage_fraction"], 0.75)
        self.assertIsNone(summary["sleep_efficiency"])
        self.assertEqual(summary["sleep_windows_excluded_for_coverage"], 1)

    def test_tst_has_no_implicit_whole_recording_fallback(self):
        index = pd.date_range("2026-04-10", periods=24, freq="1h")
        score = pd.Series(1.0, index=index)
        minutes, details = _score_minutes_in_windows(score, [], minimum_coverage=0.80)
        self.assertIsNone(minutes)
        self.assertEqual(details, [])

    def test_sleep_efficiency_denominator_uses_observed_epochs(self):
        index = pd.date_range("2026-05-01 22:00", periods=8 * 60, freq="1min")
        score = pd.Series(1.0, index=index)
        score.iloc[:30] = np.nan
        score.iloc[100:145] = 0.0
        windows = [{"start": index[0], "stop": index[0] + pd.Timedelta("8h")}]

        minutes, details = _score_minutes_in_windows(score, windows, minimum_coverage=0.80)
        summary = _compute_waso_and_efficiency(score, windows, window_quality=details)

        self.assertAlmostEqual(minutes, 405.0)
        self.assertAlmostEqual(summary["time_in_bed_minutes"], 450.0)
        self.assertAlmostEqual(summary["scheduled_time_in_bed_minutes"], 480.0)
        self.assertAlmostEqual(summary["sleep_efficiency"], 90.0)

    def test_missing_aware_sri_uses_only_real_24_hour_pairs(self):
        index = pd.date_range("2026-06-01", periods=3 * 24, freq="1h")
        score = pd.Series(np.tile([0] * 8 + [1] * 16, 3), index=index, dtype=float)
        score.loc["2026-06-02 03:00"] = np.nan
        self.assertEqual(_missing_aware_sri(score), 100.0)


    def test_standard_thresholds_remain_active_until_customization_is_enabled(self):
        standard = resolve_data_quality_settings({
            "masking": {
                "customizeDataQualityThresholds": False,
                "minimumValidHoursPerDay": 10,
                "minimumValidDaysForRhythm": 5,
                "minimumSleepWindowCoverage": 0.5,
            }
        })
        self.assertEqual(standard["minimum_valid_hours_per_day"], 16.0)
        self.assertEqual(standard["minimum_valid_days_for_rhythm"], 2)
        self.assertEqual(standard["minimum_sleep_window_coverage"], 0.8)

        custom = resolve_data_quality_settings({
            "masking": {
                "customizeDataQualityThresholds": True,
                "minimumValidHoursPerDay": 10,
                "minimumValidDaysForRhythm": 5,
                "minimumSleepWindowCoverage": 0.5,
            }
        })
        self.assertEqual(custom["minimum_valid_hours_per_day"], 10.0)
        self.assertEqual(custom["minimum_valid_days_for_rhythm"], 5)
        self.assertEqual(custom["minimum_sleep_window_coverage"], 0.5)

    def test_nonconsecutive_valid_days_do_not_satisfy_rhythm_requirement(self):
        index = pd.date_range("2026-08-01", periods=3 * 24, freq="1h")
        activity = pd.Series(4.0, index=index)
        activity.loc["2026-08-02"] = np.nan
        cleaned, quality = apply_data_quality_control(FakeRaw(activity), {
            "masking": {
                "customizeDataQualityThresholds": False,
                "respectNonwear": True,
            }
        })

        self.assertEqual(quality["valid_days"], 2)
        self.assertEqual(quality["longest_consecutive_valid_days"], 1)
        self.assertIsNone(compute_metric(cleaned, "is", {"freq": "1h"}))
        self.assertTrue(any("consecutive valid" in warning for warning in quality["warnings"]))

    def test_multiday_metric_is_not_called_when_valid_days_are_insufficient(self):
        raw = FakeRaw(pd.Series([1.0, 2.0], index=pd.date_range("2026-07-01", periods=2, freq="1h")))
        raw._ui_valid_day_count = 1
        raw._ui_min_valid_days_for_rhythm = 2

        def fail_if_called(**_kwargs):
            raise AssertionError("Metric should have been gated before execution")

        raw.IS = fail_if_called
        self.assertIsNone(compute_metric(raw, "is", {"freq": "1h"}))


if __name__ == "__main__":
    unittest.main()
