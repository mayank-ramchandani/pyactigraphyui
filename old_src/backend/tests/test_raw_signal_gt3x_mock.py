"""GT3X decoder integration using controlled low-level events (no pygt3x test dependency)."""
import tempfile
import unittest
from enum import IntEnum
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from zipfile import ZipFile

import numpy as np

from backend.gt3x_loader import prepare_gt3x_activity_series

_START = 1_577_836_800
_DOTNET = 621355968000000000


class Types(IntEnum):
    Params = 1
    Event = 2
    TemperatureRecord = 3
    Activity = 4
    Activity2 = 5
    Activity3 = 6


class Info:
    @staticmethod
    def read_zip(_archive):
        return SimpleNamespace(sample_rate=30, timezone="+00:00:00", start_date=_START * 10_000_000 + _DOTNET,
                               last_sample_time=(_START + 8) * 10_000_000 + _DOTNET)


class IdentityCalibrator:
    method = "mock_identity_g"
    def __init__(self, *_args):
        pass

    def apply(self, axes):
        return axes


class Reader:
    def __init__(self, _handle):
        self.i = 0

    def read_event(self):
        if self.i >= 4:
            return None
        stamp = _START + 2 * self.i
        self.i += 1
        return SimpleNamespace(
            header=SimpleNamespace(timestamp=stamp, event_type=Types.Activity2, payload_size=4),
            payload=b"TEST", is_checksum_valid=True
        )


def raw_axes(*_args):
    return np.array([[0.9 if i % 2 == 0 else 1.1, 0, 0] for i in range(60)], dtype=np.float32)


class GT3XRawSignalIntegration(unittest.TestCase):
    def test_configured_magnitude_normalization_reaches_epoch_activity(self):
        with tempfile.TemporaryDirectory() as d:
            file_path = Path(d) / "mock.gt3x"
            with ZipFile(file_path, "w") as archive:
                archive.writestr("log.bin", b"TEST")
            api = {"Info": Info, "Types": Types, "LogReader": Reader, "CalibrationV2Service": object()}
            with patch("backend.gt3x_loader._require_pygt3x", return_value=api), \
                 patch("backend.gt3x_loader._Calibrator", IdentityCalibrator), \
                 patch("backend.gt3x_loader._decode_axes", raw_axes):
                original, _, _ = prepare_gt3x_activity_series(str(file_path), epoch_period=2, activity_mapping="accelerometer")
                custom, metadata, _ = prepare_gt3x_activity_series(
                    str(file_path), epoch_period=2, activity_mapping="accelerometer",
                    activity_signal_settings={"rawSignal": {"enabled": True, "normalization": "absolute_deviation", "output_unit": "g"}},
                )
        self.assertEqual(len(custom), 4)
        self.assertEqual(custom.name, "ACC_g")
        np.testing.assert_allclose(custom.values, .1, atol=2e-5)
        np.testing.assert_allclose(original.values, .05 * 1000, atol=.01)
        self.assertEqual(metadata["_activity_mapping"]["units"], "g")
        self.assertTrue(metadata["_activity_mapping"]["custom_raw_processing"]["enabled"])


if __name__ == "__main__":
    unittest.main()
