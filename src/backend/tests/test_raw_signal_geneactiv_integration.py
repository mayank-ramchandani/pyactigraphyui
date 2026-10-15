"""Integration test through the native GENEActiv streaming page decoder."""
import tempfile
import unittest
from pathlib import Path

import numpy as np

from backend.geneactiv_bin import read_raw_geneactiv_bin


def sample_hex(x):
    return (int(x) << 36).to_bytes(6, "big").hex().upper()


def create_demo_bin(path):
    lines = ["X Gain: 100000", "Y Gain: 100000", "Z Gain: 100000"]
    for second in (0, 2, 4, 6):
        # 60 sample page at 30 Hz: 0.9 g, 1.1 g alternating.
        hex_data = "".join(sample_hex(900 if i % 2 == 0 else 1100) for i in range(60))
        lines.extend(["Recorded Data", f"Page Time: 2026-01-01 00:00:{second:02d}:000", "Measurement Frequency: 30", hex_data])
    path.write_text("\n".join(lines))


class NativeGeneactivSignalTest(unittest.TestCase):
    def test_raw_options_apply_and_default_is_unmodified(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "demo.bin"
            create_demo_bin(p)
            default = read_raw_geneactiv_bin(str(p), resample_freq="2s", activity_mapping="accelerometer")
            unchanged = read_raw_geneactiv_bin(str(p), resample_freq="2s", activity_mapping="accelerometer", activity_signal_settings={"rawSignal": {"enabled": False}})
            self.assertTrue(default.data.equals(unchanged.data))
            values = {}
            for normal in ("none", "positive_deviation", "absolute_deviation"):
                result = read_raw_geneactiv_bin(str(p), resample_freq="2s", activity_mapping="accelerometer", activity_signal_settings={"rawSignal": {"enabled": True, "normalization": normal, "output_unit": "g"}})
                values[normal] = result
                self.assertEqual(result.data.name, "ACC_g")
                self.assertEqual(result._ui_activity_mapping_metadata["units"], "g")
                self.assertEqual(len(result.data), 4)
                self.assertIn("custom_raw_processing", result._ui_activity_mapping_metadata)
            np.testing.assert_allclose(values["none"].data.values, 1.0)
            np.testing.assert_allclose(values["positive_deviation"].data.values, .05)
            np.testing.assert_allclose(values["absolute_deviation"].data.values, .1)

    def test_native_sample_rate_blocks_invalid_frequency(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "demo.bin"
            create_demo_bin(p)
            with self.assertRaisesRegex(ValueError, "Nyquist"):
                read_raw_geneactiv_bin(str(p), resample_freq="2s", activity_mapping="accelerometer", activity_signal_settings={"rawSignal": {"enabled": True, "filter_type": "lowpass", "high_cutoff_hz": 20}})


if __name__ == "__main__":
    unittest.main()
