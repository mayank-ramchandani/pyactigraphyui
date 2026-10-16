"""Regression: custom raw settings propagate into API activity previews."""
import io
import json
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi import UploadFile

try:
    import pyActigraphy  # noqa: F401
except ImportError:
    mock_pyactigraphy = types.ModuleType("pyActigraphy")
    mock_io = types.ModuleType("pyActigraphy.io")
    mock_io.BaseRaw = type("_TestBaseRaw", (), {})
    mock_pyactigraphy.io = mock_io
    sys.modules["pyActigraphy"] = mock_pyactigraphy
    sys.modules["pyActigraphy.io"] = mock_io

from backend.app import preview_basic
from backend.tests.test_raw_signal_geneactiv_integration import create_demo_bin


class RawSignalPreviewConsistencyTests(unittest.TestCase):
    def test_preview_uses_selected_custom_samples_and_reports_units(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "recording.bin"
            create_demo_bin(path)
            content = path.read_bytes()

            def preview(normalization):
                # The minimal synthetic fixture omits GENEActiv recognition headers.
                # Force its known file format so this test covers the preview route.
                settings = {"rawSignal": {"enabled": True, "normalization": normalization, "output_unit": "g"}}
                with patch("backend.io_helpers.looks_like_geneactiv_bin", return_value=True):
                    response = preview_basic(
                        file=UploadFile(filename="recording.bin", file=io.BytesIO(content)),
                        additionalFiles=None,
                        activityChannel="VM",
                        activityMapping="accelerometer",
                        activitySignalSettings=json.dumps(settings),
                        resampleFreq="1min",
                        csvMapping="{}",
                        csvSeparator=",",
                        maskingFiles=None,
                        sleepDiaryFiles=None,
                        startStopFiles=None,
                    )
                self.assertEqual(response.status_code, 200, response.body)
                return json.loads(response.body)

            magnitude = preview("none")
            normalized = preview("positive_deviation")
            self.assertAlmostEqual(magnitude["full_recording_preview"][0]["activity"], 1.0, places=6)
            self.assertAlmostEqual(normalized["full_recording_preview"][0]["activity"], 0.05, places=6)
            for payload in (magnitude, normalized):
                self.assertEqual(payload["activity_mapping"]["units"], "g")
                self.assertTrue(payload["activity_mapping"]["custom_raw_processing"]["enabled"])
                self.assertEqual(payload["activity_mapping"]["resolved"], "accelerometer")


if __name__ == "__main__":
    unittest.main()
