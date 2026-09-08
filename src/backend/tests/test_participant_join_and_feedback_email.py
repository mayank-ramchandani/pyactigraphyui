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
