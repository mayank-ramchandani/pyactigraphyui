"""Regression tests for release outputs and schema/epoch decisions."""
import sys
import types
import unittest
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd

try:
    import pyActigraphy
except ImportError:
    fake = types.ModuleType("pyActigraphy")
    io = types.ModuleType("pyActigraphy.io")
    class BaseRaw:
        def __init__(self, **fields):
            self.__dict__.update(fields)
            self._data = fields.get("data")
        @property
        def data(self): return self._data
        @data.setter
        def data(self, v): self._data = v
    io.BaseRaw = BaseRaw
    fake.io = io
    sys.modules["pyActigraphy"] = fake
    sys.modules["pyActigraphy.io"] = io

from backend.activity_mapping import normalize_activity_signal_settings
from backend.tabular_xyz import detect_xyz_mapping, load_xyz_as_baseraw
from backend.release_exports import build_release_tables, effective_methods_manifest


class ReleaseFeatureTests(unittest.TestCase):
    def test_epochs_are_validated_and_part_of_effective_settings(self):
        result = normalize_activity_signal_settings({"epochSeconds": 5}, "enmo")
        self.assertEqual(result["epoch_seconds"], 5)
        self.assertEqual(normalize_activity_signal_settings({}, "auto")["epoch_seconds"], 30)
        for bad in (0, -3, 17, "bad"):
            with self.assertRaises(ValueError):
                normalize_activity_signal_settings({"epochSeconds": bad}, "auto")

    def test_detect_xyz_only_infers_units_from_unambiguous_headers(self):
        resolved = detect_xyz_mapping(["timestamp", "x_g", "y_g", "z_g", "lux"])
        self.assertEqual(resolved["x_col"], "x_g")
        self.assertEqual(resolved["acceleration_unit"], "g")
        self.assertIsNone(detect_xyz_mapping(["time", "x", "y", "z"])["acceleration_unit"])

    def test_xyz_enmo_works_with_g_and_mg_and_requires_units(self):
        base = pd.DataFrame({"timestamp": pd.date_range("2026-01-01", periods=10, freq="s").astype(str), "x_g": [1.02] * 10, "y_g": [0] * 10, "z_g": [0] * 10})
        mapping = {"timestamp_col": "timestamp", "x_col": "x_g", "y_col": "y_g", "z_col": "z_g", "acceleration_unit": "g"}
        raw = load_xyz_as_baseraw(base, mapping, name="raw.csv", epoch_seconds=5, activity_mapping="enmo")
        self.assertAlmostEqual(float(raw.data.iloc[0]), 20, places=4)
        self.assertEqual(len(raw.data), 2)
        self.assertFalse(raw._ui_tabular_xyz_info["auto_calibration_applied"])
        base[["x_g", "y_g", "z_g"]] *= 1000
        raw_mg = load_xyz_as_baseraw(base, {**mapping, "acceleration_unit": "mg"}, name="raw.csv", epoch_seconds=5, activity_mapping="enmo")
        self.assertAlmostEqual(float(raw_mg.data.iloc[0]), 20, places=4)
        with self.assertRaises(ValueError):
            load_xyz_as_baseraw(base, {**mapping, "acceleration_unit": None}, name="raw.csv")

    def test_release_levels_do_not_fake_daily_ra_or_average_sri(self):
        index = pd.date_range("2026-01-01", periods=4, freq="12h")
        raw = types.SimpleNamespace(
            _ui_source_activity_series=pd.Series([10.0, 20.0, 30.0, 40.0], index=index),
            _ui_analysis_valid_mask=pd.Series([True, True, True, False], index=index),
        )
        qc = {"recording_start": index[0].isoformat(), "recording_end": index[-1].isoformat(), "epoch_seconds": 43200,
              "valid_day_window_mode": "calendar_day", "daily_qc": [
                {"window_start": "2026-01-01", "window_stop": "2026-01-02", "date": "2026-01-01", "valid_day": True},
                {"window_start": "2026-01-02", "window_stop": "2026-01-03", "date": "2026-01-02", "valid_day": True}]}
        output = build_release_tables(raw, {"ra": 0.7, "sri": 0.85, "sleep_windows": [{"date":"x"}]}, qc, source_name="participant.csv")
        self.assertEqual(output["daily_rows"][0]["activity_mean_valid_epochs"], 15.0)
        self.assertEqual(output["daily_rows"][1]["activity_mean_valid_epochs"], 30.0)
        self.assertNotIn("ra", output["daily_rows"][0])
        self.assertEqual(output["aggregated_rows"][0]["ra"], 0.7)
        self.assertEqual(output["aggregated_rows"][0]["activity_mean_valid_epochs"], 20.0)

    def test_http_loader_auto_detects_xyz_csv_and_uses_selected_epoch(self):
        from backend.app import _load_native_supported_file
        frame = pd.DataFrame({"timestamp": pd.date_range("2026-01-01", periods=10, freq="s").astype(str),
                              "x_g": [1.01] * 10, "y_g": [0] * 10, "z_g": [0] * 10})
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "xyz.csv"
            frame.to_csv(path, index=False)
            raw, reader_type = _load_native_supported_file(
                str(path), activity_mapping="enmo",
                activity_signal_settings=normalize_activity_signal_settings({"epochSeconds": 5}, "enmo"),
            )
            self.assertEqual(reader_type, "tabular_raw_xyz")
            self.assertEqual(len(raw.data), 2)
            self.assertAlmostEqual(float(raw.data.iloc[0]), 10, places=4)
            # Ambiguous unit must not silently default to g.
            frame.rename(columns={"x_g": "x", "y_g": "y", "z_g": "z"}).to_csv(path, index=False)
            with self.assertRaisesRegex(ValueError, "Specify acceleration units"):
                _load_native_supported_file(str(path), activity_mapping="enmo",
                    activity_signal_settings=normalize_activity_signal_settings({"epochSeconds": 5}, "enmo"))

    def test_native_raw_epoch_flows_through_loader(self):
        from unittest.mock import patch
        from backend.io_helpers import load_native_file
        signal = normalize_activity_signal_settings({"epochSeconds": 5}, "enmo")
        with patch("backend.io_helpers.load_gt3x_as_baseraw") as mocked:
            load_native_file("example.gt3x", "gt3x", activity_mapping="enmo", activity_signal_settings=signal)
            self.assertEqual(mocked.call_args.kwargs["epoch_period"], 5)
        with patch("backend.io_helpers.read_raw_geneactiv_bin") as mocked:
            load_native_file("example.bin", "geneactiv_bin_accelerometer", activity_mapping="enmo", activity_signal_settings=signal)
            self.assertEqual(mocked.call_args.kwargs["resample_freq"], "5s")

    def test_daily_sleep_is_assigned_to_window_start_date_not_fabricated(self):
        index = pd.date_range("2026-01-01", periods=2, freq="12h")
        raw = types.SimpleNamespace(_ui_source_activity_series=pd.Series([10, 20], index=index),
                                    _ui_analysis_valid_mask=pd.Series([True, True], index=index))
        qc = {"valid_day_window_mode": "calendar_day", "daily_qc": [
            {"date": "2026-01-01", "window_start": "2026-01-01", "window_stop": "2026-01-02", "valid_day": True}]}
        results = {"sleep_window_nights": [{"sleep_night_start_date": "2026-01-01", "sleep_window_valid": True,
                  "sleep_tst_minutes": 400, "sleep_waso_minutes": 30, "sleep_observed_minutes": 450}]}
        day = build_release_tables(raw, results, qc, source_name="a")["daily_rows"][0]
        self.assertEqual(day["sleep_tst_minutes"], 400)
        self.assertEqual(day["sleep_waso_minutes"], 30)
        self.assertAlmostEqual(day["sleep_efficiency_percent"], 88.888889, places=5)
        no_score = build_release_tables(raw, {"sleep_window_nights": [
             {"sleep_night_start_date": "2026-01-01", "sleep_window_valid": False,
              "sleep_tst_minutes": None, "sleep_waso_minutes": None}]}, qc, source_name="a")["daily_rows"][0]
        self.assertNotIn("sleep_tst_minutes", no_score)

    def test_metadata_includes_untouched_defaults(self):
        manifest = effective_methods_manifest(file_names=["recording.csv"], reader_type="tabular_mapped",
            activity_mapping={"requested":"auto", "resolved":"original"}, settings={}, analysis_config={}, data_quality={}, provenance={})
        self.assertEqual(manifest["effective_activity_signal_settings"]["epoch_seconds"], 30)
        self.assertFalse(manifest["raw_signal_defaults"]["enabled"])
        self.assertEqual(manifest["effective_quality_settings"]["minimum_valid_hours_per_day"], 16.0)

if __name__ == "__main__": unittest.main()
