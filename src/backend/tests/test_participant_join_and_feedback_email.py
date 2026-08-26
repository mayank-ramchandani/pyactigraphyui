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


class DummyRaw:
    def __init__(self, series):
        self.data = series
        self.metadata = {}
        self.name = "dummy"

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
