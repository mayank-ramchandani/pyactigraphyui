import os
import sys
import types
import unittest
from unittest import mock

import pandas as pd

try:
    import pyActigraphy  # noqa: F401
except Exception:
    pyactigraphy_module = types.ModuleType("pyActigraphy")
    pyactigraphy_io_module = types.ModuleType("pyActigraphy.io")

    class _TestBaseRaw:
        pass

    pyactigraphy_io_module.BaseRaw = _TestBaseRaw
    pyactigraphy_module.io = pyactigraphy_io_module
    sys.modules["pyActigraphy"] = pyactigraphy_module
    sys.modules["pyActigraphy.io"] = pyactigraphy_io_module

from backend import app as app_module
from backend.geneactiv_bin import SimpleLightRecording


class DummyRaw:
    def __init__(self, series, light_channels=None):
        self.data = series
        self.metadata = {}
        self.name = "dummy"
        self.light = SimpleLightRecording(light_channels or {}) if light_channels else None

    @property
    def raw_data(self):
        return self.data


class ParticipantJoinTests(unittest.TestCase):
    def test_join_preserves_gap_and_removes_duplicate_boundary_timestamp(self):
        first_index = pd.date_range("2026-01-01 00:00", periods=4, freq="1min")
        second_index = pd.date_range("2026-01-01 00:03", periods=4, freq="1min")
        first = DummyRaw(pd.Series([1, 2, 3, 4], index=first_index))
        second = DummyRaw(pd.Series([40, 5, 6, 7], index=second_index))

        joined, metadata = app_module._concatenate_raw_recordings(
            [first, second], ["part1.csv", "part2.csv"]
        )

        self.assertTrue(metadata["joined"])
        self.assertEqual(metadata["source_file_count"], 2)
        self.assertEqual(metadata["duplicate_timestamps_removed"], 1)
        self.assertEqual(len(joined.data), 7)
        self.assertEqual(joined.data.loc[pd.Timestamp("2026-01-01 00:03")], 4)

    def test_join_concatenates_light_channels_by_timestamp_and_preserves_gap(self):
        first_index = pd.date_range("2026-01-01 00:00", periods=4, freq="1min")
        second_index = pd.date_range("2026-01-01 00:10", periods=4, freq="1min")
        first = DummyRaw(
            pd.Series([1, 2, 3, 4], index=first_index),
            {"LIGHT": pd.Series([10, 20, 30, 40], index=first_index)},
        )
        second = DummyRaw(
            pd.Series([5, 6, 7, 8], index=second_index),
            {"LIGHT": pd.Series([50, 60, 70, 80], index=second_index)},
        )

        joined, metadata = app_module._concatenate_raw_recordings(
            [first, second], ["part1.csv", "part2.csv"]
        )

        joined_light = joined.light.get_channel("LIGHT")
        self.assertEqual(len(joined_light), 8)
        self.assertEqual(joined_light.loc[pd.Timestamp("2026-01-01 00:10")], 50)
        self.assertNotIn(pd.Timestamp("2026-01-01 00:05"), joined_light.index)
        self.assertTrue(metadata["light"]["available"])
        self.assertEqual(metadata["light"]["source_file_count_with_light"], 2)

    def test_join_light_uses_first_value_at_duplicate_boundary(self):
        first_index = pd.date_range("2026-01-01 00:00", periods=4, freq="1min")
        second_index = pd.date_range("2026-01-01 00:03", periods=4, freq="1min")
        first = DummyRaw(
            pd.Series([1, 2, 3, 4], index=first_index),
            {"LIGHT": pd.Series([10, 20, 30, 40], index=first_index)},
        )
        second = DummyRaw(
            pd.Series([5, 6, 7, 8], index=second_index),
            {"LIGHT": pd.Series([400, 50, 60, 70], index=second_index)},
        )

        joined, metadata = app_module._concatenate_raw_recordings(
            [first, second], ["part1.csv", "part2.csv"]
        )
        joined_light = joined.light.get_channel("LIGHT")
        self.assertEqual(joined_light.loc[pd.Timestamp("2026-01-01 00:03")], 40)
        self.assertEqual(metadata["light"]["duplicate_timestamps_removed"]["LIGHT"], 1)

    def test_join_rejects_incompatible_light_sampling_intervals(self):
        activity_index_a = pd.date_range("2026-01-01", periods=4, freq="1min")
        activity_index_b = pd.date_range("2026-01-02", periods=4, freq="1min")
        first = DummyRaw(
            pd.Series([1, 2, 3, 4], index=activity_index_a),
            {"LIGHT": pd.Series([10, 20, 30, 40], index=activity_index_a)},
        )
        second_light_index = pd.date_range("2026-01-02", periods=4, freq="5min")
        second = DummyRaw(
            pd.Series([5, 6, 7, 8], index=activity_index_b),
            {"LIGHT": pd.Series([50, 60, 70, 80], index=second_light_index)},
        )
        with self.assertRaisesRegex(ValueError, "light channel LIGHT requires compatible sampling intervals"):
            app_module._concatenate_raw_recordings([first, second], ["a.csv", "b.csv"])

    def test_join_rejects_incompatible_sampling_intervals(self):
        first = DummyRaw(pd.Series([1, 2, 3], index=pd.date_range("2026-01-01", periods=3, freq="1min")))
        second = DummyRaw(pd.Series([4, 5, 6], index=pd.date_range("2026-01-02", periods=3, freq="5min")))
        with self.assertRaisesRegex(ValueError, "compatible sampling intervals"):
            app_module._concatenate_raw_recordings([first, second], ["a.csv", "b.csv"])

    def test_join_rebuilds_read_only_pyactigraphy_baseraw_instead_of_leaving_first_file_only(self):
        class ReadOnlyBaseRaw:
            def __init__(self, name, uuid, format, axial_mode, start_time, period, frequency, data, light, fpath=None):
                self._name = name
                self._uuid = uuid
                self._format = format
                self._axial_mode = axial_mode
                self._start_time = start_time
                self._period = period
                self._frequency = frequency
                self._raw_data = data
                self._light = light
                self.fpath = fpath
                self.display_name = name
                self.metadata = {}
                self.mask = None

            @property
            def name(self):
                return self._name

            @property
            def uuid(self):
                return self._uuid

            @property
            def format(self):
                return self._format

            @property
            def axial_mode(self):
                return self._axial_mode

            @property
            def start_time(self):
                return self._start_time

            @start_time.setter
            def start_time(self, value):
                self._start_time = value

            @property
            def period(self):
                return self._period

            @period.setter
            def period(self, value):
                self._period = value

            @property
            def frequency(self):
                return self._frequency

            @property
            def raw_data(self):
                return self._raw_data

            @property
            def data(self):
                return self._raw_data.loc[self.start_time:self.start_time + self.period]

            @property
            def light(self):
                return self._light

            @property
            def raw_light(self):
                return self._light

        first_index = pd.date_range("2017-06-29", periods=6, freq="1min")
        second_index = pd.date_range("2019-09-17", periods=4, freq="1min")
        first = ReadOnlyBaseRaw("first", "a", "GT3X", None, first_index[0], first_index[-1] - first_index[0], pd.Timedelta(minutes=1), pd.Series(range(6), index=first_index), None)
        second = ReadOnlyBaseRaw("second", "b", "GT3X", None, second_index[0], second_index[-1] - second_index[0], pd.Timedelta(minutes=1), pd.Series(range(10, 14), index=second_index), None)

        with mock.patch.object(app_module, "PyActigraphyBaseRaw", ReadOnlyBaseRaw):
            joined, metadata = app_module._concatenate_raw_recordings([first, second], ["2017.gt3x", "2019.gt3x"])

        self.assertTrue(metadata["joined"])
        self.assertEqual(joined.data.index.min(), first_index[0])
        self.assertEqual(joined.data.index.max(), second_index[-1])
        self.assertEqual(joined.data.loc[second_index[0]], 10)
        self.assertEqual(len(metadata["segments"]), 2)

    def test_joined_preview_keeps_short_late_segment_visible_across_multi_year_gap(self):
        first_index = pd.date_range("2017-04-24", periods=24 * 60, freq="1min")
        second_index = pd.date_range("2019-09-17 18:40", periods=41, freq="1min")
        first = DummyRaw(pd.Series(range(len(first_index)), index=first_index, dtype=float))
        second = DummyRaw(pd.Series(range(len(second_index)), index=second_index, dtype=float))

        joined, metadata = app_module._concatenate_raw_recordings([first, second], ["2017.gt3x", "2019.gt3x"])
        preview = app_module.build_native_preview(joined, activity_channel="activity", resample_freq="1min")

        timestamps = [row["timestamp"] for row in preview["full_recording_preview"] if not row.get("is_gap")]
        self.assertTrue(any(ts.startswith("2017-") for ts in timestamps))
        self.assertTrue(any(ts.startswith("2019-") for ts in timestamps))
        self.assertTrue(any(row.get("is_gap") for row in preview["full_recording_preview"]))
        # The preview should not materialise every empty minute between 2017 and 2019.
        self.assertLess(preview["summary"]["rows"], 2000)
        self.assertEqual(metadata["segments"][1]["source_file"], "2019.gt3x")

    def _raw_with_rate_and_mapping(self, start, rate_hz, mapping):
        index = pd.date_range(start, periods=4, freq="30s")
        raw = DummyRaw(pd.Series([1.0, 2.0, 3.0, 4.0], index=index))
        raw._ui_gt3x_summary = {"sample_rate": rate_hz}
        raw._ui_activity_mapping_metadata = app_module.mapping_metadata(mapping, mapping)
        raw._ui_activity_mapping = mapping
        raw._ui_activity_mapping_requested = mapping
        raw._ui_activity_units = app_module.mapping_metadata(mapping, mapping).get("units")
        return raw

    def test_different_native_rates_enmo_join_with_information(self):
        first = self._raw_with_rate_and_mapping("2026-01-01", 30, "enmo")
        second = self._raw_with_rate_and_mapping("2026-01-02", 100, "enmo")
        joined, metadata = app_module._concatenate_raw_recordings([first, second], ["30hz.gt3x", "100hz.gt3x"])
        harmonization = metadata["sampling_harmonization"]
        self.assertTrue(harmonization["native_rates_differ"])
        self.assertEqual(harmonization["severity"], "info")
        self.assertEqual(harmonization["decision"], "allowed_with_information")
        self.assertEqual(harmonization["native_sample_rates_hz"], [30.0, 100.0])
        self.assertEqual(harmonization["processed_epoch_seconds"], 30.0)
        self.assertFalse(harmonization["raw_frequency_resampled"])
        self.assertEqual(len(joined.data), 8)

    def test_different_native_rates_mad_and_pim_join_with_warning(self):
        for mapping in ("mad", "pim"):
            with self.subTest(mapping=mapping):
                first = self._raw_with_rate_and_mapping("2026-01-01", 30, mapping)
                second = self._raw_with_rate_and_mapping("2026-01-02", 100, mapping)
                _, metadata = app_module._concatenate_raw_recordings([first, second], ["30hz.gt3x", "100hz.gt3x"])
                self.assertEqual(metadata["sampling_harmonization"]["severity"], "warning")
                self.assertIn(mapping.upper(), metadata["sampling_harmonization"]["message"])

    def test_different_native_rates_zcm_join_with_strong_warning(self):
        first = self._raw_with_rate_and_mapping("2026-01-01", 30, "zcm")
        second = self._raw_with_rate_and_mapping("2026-01-02", 100, "zcm")
        _, metadata = app_module._concatenate_raw_recordings([first, second], ["30hz.gt3x", "100hz.gt3x"])
        harmonization = metadata["sampling_harmonization"]
        self.assertEqual(harmonization["severity"], "strong_warning")
        self.assertIn("sampling frequency", harmonization["message"])

    def test_different_native_rates_source_activity_is_blocked(self):
        first = self._raw_with_rate_and_mapping("2026-01-01", 30, "original")
        second = self._raw_with_rate_and_mapping("2026-01-02", 100, "original")
        with self.assertRaisesRegex(ValueError, "does not join source/device activity or ActiGraph counts"):
            app_module._concatenate_raw_recordings([first, second], ["30hz.gt3x", "100hz.gt3x"])

    def test_joined_light_preview_keeps_each_source_visible_across_multi_year_gap(self):
        first_index = pd.date_range("2017-04-24", periods=240, freq="1min")
        second_index = pd.date_range("2019-09-17 18:40", periods=41, freq="1min")
        first = DummyRaw(
            pd.Series(range(len(first_index)), index=first_index, dtype=float),
            {"LIGHT": pd.Series(range(len(first_index)), index=first_index, dtype=float)},
        )
        second = DummyRaw(
            pd.Series(range(len(second_index)), index=second_index, dtype=float),
            {"LIGHT": pd.Series(range(len(second_index)), index=second_index, dtype=float)},
        )
        joined, _ = app_module._concatenate_raw_recordings([first, second], ["2017.gt3x", "2019.gt3x"])
        preview = app_module.build_light_preview(joined, resample_freq="1min")
        timestamps = [row["timestamp"] for row in preview["light_preview"] if not row.get("is_gap")]
        self.assertTrue(any(ts.startswith("2017-") for ts in timestamps))
        self.assertTrue(any(ts.startswith("2019-") for ts in timestamps))
        self.assertTrue(any(row.get("is_gap") for row in preview["light_preview"]))


class FeedbackNotificationTests(unittest.TestCase):
    @mock.patch("backend.app.smtplib.SMTP")
    def test_notification_is_minimal_and_excludes_feedback_text(self, smtp_cls):
        smtp = smtp_cls.return_value.__enter__.return_value
        record = {
            "id": "feedback-123",
            "email": "user@example.com",
            "file_name": "watch.gt3x",
            "current_step": "9",
            "category": "issue",
            "message": "THIS SHOULD NEVER BE EMAILED",
            "configuration": {"secret_detail": "also excluded"},
        }
        env = {
            "SMTP_HOST": "smtp.example.com",
            "SMTP_PORT": "587",
            "SMTP_FROM": "noreply@example.com",
            "SMTP_USERNAME": "mailer",
            "SMTP_PASSWORD": "password",
            "SMTP_USE_TLS": "true",
        }
        with mock.patch.dict(os.environ, env, clear=False):
            result = app_module._send_feedback_notification(record)

        self.assertTrue(result["sent"])
        smtp.send_message.assert_called_once()
        message = smtp.send_message.call_args.args[0]
        body = message.get_content()
        self.assertIn("user@example.com", body)
        self.assertIn("watch.gt3x", body)
        self.assertIn("Step: 9", body)
        self.assertNotIn(record["message"], body)
        self.assertNotIn("secret_detail", body)


if __name__ == "__main__":
    unittest.main()
