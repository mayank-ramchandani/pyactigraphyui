import struct
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch
from zipfile import ZIP_DEFLATED, ZipFile

import numpy as np

from backend.gt3x_loader import (
    _StreamingCounts30,
    load_gt3x_light_as_raw,
    prepare_gt3x_activity_series,
    prepare_gt3x_light_series,
)


DOTNET_TO_UNIX_TICKS = 621355968000000000


def _dotnet_ticks(unix_seconds: int) -> int:
    return int(unix_seconds * 10_000_000 + DOTNET_TO_UNIX_TICKS)


def _event(timestamp: int, event_type: int, payload: bytes, separator: int = 0x1E) -> bytes:
    header = struct.pack("<BBLH", separator, event_type, timestamp, len(payload))
    checksum = separator ^ event_type
    for value in timestamp.to_bytes(4, "little"):
        checksum ^= value
    for value in len(payload).to_bytes(4, "little"):
        checksum ^= value
    for value in payload:
        checksum ^= value
    checksum = (~checksum) & 0xFF
    return header + payload + bytes([checksum])


def _activity2_payload(x_values: np.ndarray) -> bytes:
    axes = np.zeros((len(x_values), 3), dtype="<i2")
    axes[:, 0] = np.asarray(x_values, dtype=np.int16)
    return axes.tobytes()


def _write_gt3x(path: Path, start: int, stop: int, events: list[bytes]) -> None:
    info = "\n".join(
        [
            "Serial Number: TEST123",
            "Device Type: Link",
            "Firmware: 1.3.0",
            "Battery Voltage: 4.0",
            "Sample Rate: 30",
            f"Start Date: {_dotnet_ticks(start)}",
            "Stop Date: 0",
            f"Last Sample Time: {_dotnet_ticks(stop)}",
            "TimeZone: -04:00:00",
            "Acceleration Scale: 256.0",
            "Acceleration Min: -8.0",
            "Acceleration Max: 8.0",
            "Unexpected Resets: 0",
        ]
    )
    with ZipFile(path, "w", compression=ZIP_DEFLATED) as archive:
        archive.writestr("info.txt", info + "\n")
        archive.writestr("log.bin", b"".join(events))


class StreamingGT3XTests(unittest.TestCase):
    def test_streamed_lux_records_are_detected_aggregated_and_gap_preserving(self):
        start = 1_577_836_800
        events = [
            _event(start + 0, 5, struct.pack("<H", 10)),
            _event(start + 1, 5, struct.pack("<H", 20)),
            _event(start + 4, 5, struct.pack("<H", 100)),
        ]

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "light.gt3x"
            _write_gt3x(path, start, start + 4, events)
            light_lux, metadata = prepare_gt3x_light_series(str(path), epoch_period=2)
            raw = load_gt3x_light_as_raw(str(path), epoch_period=2)

        self.assertEqual(str(light_lux.index[0]), "2019-12-31 20:00:00")
        self.assertEqual(str(light_lux.index[-1]), "2019-12-31 20:00:04")
        np.testing.assert_allclose(
            light_lux.to_numpy(),
            [15.0, np.nan, 100.0],
            equal_nan=True,
        )
        self.assertTrue(metadata["_gt3x_light_available"])
        self.assertEqual(metadata["_gt3x_lux_records"], 3)
        self.assertEqual(raw.light.get_channel_list(), ["LIGHT", "LIGHT_LUX"])
        np.testing.assert_allclose(
            raw.light.get_channel("LIGHT").to_numpy(),
            np.log10(np.asarray([15.0, 100.0]) + 1.0),
        )

    def test_gt3x_without_lux_records_returns_explicit_no_light_result(self):
        start = 1_577_836_800
        constant = np.full(30, 282, dtype=np.int16)
        events = [_event(start, 26, _activity2_payload(constant))]

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "no-light.gt3x"
            _write_gt3x(path, start, start + 1, events)
            light_lux, metadata = prepare_gt3x_light_series(str(path), epoch_period=2)
            raw = load_gt3x_light_as_raw(str(path), epoch_period=2)

        self.assertTrue(light_lux.empty)
        self.assertFalse(metadata["_gt3x_light_available"])
        self.assertEqual(metadata["_gt3x_lux_records"], 0)
        self.assertEqual(raw.light.get_channel_list(), [])

    def test_auto_mapping_preserves_gaps_timezone_and_rejects_bad_timestamp(self):
        start = 1_577_836_800  # 2020-01-01 00:00:00 UTC
        constant = np.full(30, 282, dtype=np.int16)
        events = [
            _event(start + second, 26, _activity2_payload(constant))
            for second in (0, 1, 4, 5)
        ]
        events.append(_event(4_292_462_550, 26, _activity2_payload(constant)))

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "gapped.gt3x"
            _write_gt3x(path, start, start + 5, events)
            activity, metadata, preview = prepare_gt3x_activity_series(
                str(path), epoch_period=2, activity_mapping="auto"
            )

        self.assertEqual(str(activity.index[0]), "2019-12-31 20:00:00")
        self.assertEqual(str(activity.index[-1]), "2019-12-31 20:00:04")
        self.assertEqual(len(activity), 3)
        self.assertEqual(int(activity.notna().sum()), 2)
        self.assertTrue(np.isnan(activity.iloc[1]))
        self.assertAlmostEqual(float(activity.iloc[0]), (282 / 256 - 1) * 1000, places=6)
        self.assertAlmostEqual(float(activity.iloc[2]), (282 / 256 - 1) * 1000, places=6)
        self.assertEqual(metadata["_raw_rows"], 120)
        self.assertEqual(metadata["_invalid_timestamp_activity_events_skipped"], 1)
        self.assertTrue(metadata["_streaming_loader"])
        self.assertEqual(metadata["_activity_mapping"]["resolved"], "accelerometer")
        self.assertEqual(len(preview), 5)
        self.assertAlmostEqual(float(preview.iloc[0]["X"]), 282 / 256, places=6)

    def test_mad_is_computed_within_each_epoch(self):
        start = 1_577_836_800
        alternating = np.tile(np.asarray([256, 307], dtype=np.int16), 15)
        events = [
            _event(start + second, 26, _activity2_payload(alternating))
            for second in range(4)
        ]

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "mad.gt3x"
            _write_gt3x(path, start, start + 3, events)
            activity, metadata, _ = prepare_gt3x_activity_series(
                str(path), epoch_period=2, activity_mapping="mad"
            )

        calibrated = alternating.astype(float) / 256.0
        expected = float(np.mean(np.abs(calibrated - calibrated.mean())) * 1000.0)
        self.assertEqual(int(activity.notna().sum()), 2)
        np.testing.assert_allclose(activity.dropna().to_numpy(), [expected, expected], rtol=1e-6)
        self.assertEqual(metadata["_gt3x_activity_mode"], "mad")
        self.assertEqual(metadata["_activity_mapping"]["resolved"], "mad")

    def test_streaming_counts_keeps_filter_and_group_state_across_chunks(self):
        from scipy.signal import lfilter, lfilter_zi

        coefficients_in = np.asarray([[0.1, 0.1]], dtype=float)
        coefficients_out = np.asarray([[1.0, -0.8]], dtype=float)
        package = types.ModuleType("agcounts")
        legacy = types.ModuleType("agcounts.legacy")
        legacy.INPUT_COEFFICIENTS = coefficients_in
        legacy.OUTPUT_COEFFICIENTS = coefficients_out

        sample = np.arange(120, dtype=float)
        axes = np.column_stack(
            (
                1.0 + 0.2 * np.sin(sample / 4.0),
                0.5 * np.cos(sample / 7.0),
                0.1 * np.sin(sample / 3.0),
            )
        )
        with patch.dict(sys.modules, {"agcounts": package, "agcounts.legacy": legacy}):
            accumulator = _StreamingCounts30(epoch_seconds=2, sample_rate=30)
            accumulator.add(axes[:47], start_seconds=0.0)
            accumulator.add(axes[47:], start_seconds=47 / 30.0)
            streamed = accumulator.series().dropna().to_numpy()

        data = np.round(axes.T, decimals=3)
        zi = lfilter_zi(coefficients_in[0], coefficients_out[0]).reshape((1, -1))
        state = zi.repeat(3, axis=0) * data[:, 0].reshape((-1, 1))
        filtered, _ = lfilter(coefficients_in[0], coefficients_out[0], data, zi=state)
        filtered *= (3.0 / 4096.0) / (2.6 / 256.0) * 237.5
        trimmed = np.floor(np.clip(np.where(np.abs(filtered) < 4, 0, np.abs(filtered)), 0, 128))
        ten_hz = np.floor(trimmed.reshape(3, -1, 3).sum(axis=2) / 3.0)
        axis_epochs = ten_hz.reshape(3, -1, 20).sum(axis=2)
        expected = np.sqrt(np.square(axis_epochs).sum(axis=0))
        np.testing.assert_allclose(streamed, expected, rtol=0, atol=0)


if __name__ == "__main__":
    unittest.main()
