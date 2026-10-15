"""Regression coverage for the optional Step 2 raw-acceleration pipeline."""
import unittest

import numpy as np

from backend.activity_mapping import normalize_activity_signal_settings
from backend.raw_signal_processing import (
    RawSignalProcessor,
    normalize_raw_signal_settings,
    output_unit_factor,
    raw_signal_units,
)


class RawSignalProcessingTests(unittest.TestCase):
    def test_defaults_are_opt_in_and_preserve_old_signal_settings(self):
        config = normalize_activity_signal_settings({"thresholdMethod": "fixed", "thresholdMg": 8}, "zcm")
        self.assertFalse(config["raw_signal"]["enabled"])
        self.assertEqual(config["threshold_mg"], 8)

    def test_raw_magnitude_and_each_normalization(self):
        axes = np.array([[1.0, 0, 0], [1.1, 0, 0], [0.9, 0, 0]], dtype=float)
        expected = {
            "none": [1000, 1100, 900],
            "absolute": [1000, 1100, 900],
            "subtract_one": [0, 100, -100],
            "absolute_deviation": [0, 100, 100],
            "positive_deviation": [0, 100, 0],
        }
        for norm, values in expected.items():
            with self.subTest(norm=norm):
                p = RawSignalProcessor({"enabled": True, "normalization": norm})
                np.testing.assert_allclose(p.apply(axes, 0, 25), values, atol=1e-8)

    def test_axis_filter_and_magnitude_filter_have_distinct_results(self):
        time = np.arange(1000) / 40
        axes = np.column_stack([np.cos(time * 2 * np.pi), np.sin(time * 2 * np.pi), np.zeros(len(time))])
        base = {"enabled": True, "filter_type": "lowpass", "high_cutoff_hz": 0.5, "normalization": "none"}
        first = RawSignalProcessor({**base, "filter_stage": "axes"}).apply(axes, 0, 40)
        second = RawSignalProcessor({**base, "filter_stage": "magnitude"}).apply(axes, 0, 40)
        self.assertGreater(float(np.mean(np.abs(first - second))), 100)

    def test_chunking_matches_contiguous_processing_and_gaps_reset_filter(self):
        time = np.arange(900) / 30
        axes = np.column_stack([np.ones(len(time)), 0.2 * np.sin(2 * np.pi * time), np.zeros(len(time))])
        cfg = {"enabled": True, "filter_type": "lowpass", "high_cutoff_hz": 2.5, "normalization": "none"}
        entire = RawSignalProcessor(cfg).apply(axes, 0, 30)
        p = RawSignalProcessor(cfg)
        chunks = np.r_[p.apply(axes[:250], 0, 30), p.apply(axes[250:], 250 / 30, 30)]
        np.testing.assert_allclose(entire, chunks, atol=1e-7)
        self.assertEqual(p.resets, 0)
        p.apply(axes[:100], 100, 30)
        self.assertEqual(p.resets, 1)

    def test_nyquist_and_configuration_validation(self):
        with self.assertRaisesRegex(ValueError, "Nyquist"):
            RawSignalProcessor({"enabled": True, "filter_type": "lowpass", "high_cutoff_hz": 20, "normalization": "none"}).apply(np.ones((40, 3)), 0, 30)
        with self.assertRaisesRegex(ValueError, "static gravity"):
            normalize_raw_signal_settings({"enabled": True, "filter_type": "bandpass", "normalization": "positive_deviation"})
        with self.assertRaisesRegex(ValueError, "lower cutoff"):
            normalize_raw_signal_settings({"filter_type": "bandpass", "low_cutoff_hz": 5, "high_cutoff_hz": 2})
        with self.assertRaisesRegex(ValueError, "ENMO requires"):
            normalize_activity_signal_settings({"rawSignal": {"enabled": True, "normalization": "none"}}, "enmo")
        with self.assertRaisesRegex(ValueError, "original device"):
            normalize_activity_signal_settings({"rawSignal": {"enabled": True}}, "original")

    def test_result_units_conversion(self):
        self.assertAlmostEqual(1000 * output_unit_factor({"output_unit": "g"}), 1.0)
        self.assertAlmostEqual(1000 * output_unit_factor({"output_unit": "m_s2"}), 9.80665)
        self.assertEqual(raw_signal_units({"output_unit": "m_s2"}, "pim"), "m/s²·s/epoch")
        self.assertEqual(raw_signal_units({"output_unit": "g"}, "zcm"), "crossings/epoch")


if __name__ == "__main__":
    unittest.main()
