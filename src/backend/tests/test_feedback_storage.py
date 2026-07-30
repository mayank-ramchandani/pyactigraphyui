import asyncio
import csv
import io
import json
import os
import sys
import tempfile
import types
from datetime import datetime, timedelta, timezone
import unittest
from unittest.mock import patch

from fastapi import HTTPException
from pydantic import ValidationError
from starlette.requests import Request

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

from backend.app import FeedbackPayload, export_feedback, list_feedback, submit_feedback


def _request(token: str) -> Request:
    return Request({
        "type": "http",
        "method": "GET",
        "path": "/api/admin/feedback",
        "headers": [(b"x-feedback-admin-token", token.encode("utf-8"))],
        "query_string": b"",
        "server": ("testserver", 80),
        "client": ("127.0.0.1", 1234),
        "scheme": "http",
    })


class FeedbackStorageTests(unittest.TestCase):
    def test_feedback_is_stored_with_context_and_exported(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(
            os.environ,
            {"APP_DATA_DIR": directory, "FEEDBACK_ADMIN_TOKEN": "test-admin-secret"},
            clear=False,
        ):
            payload = FeedbackPayload(
                category="issue",
                message="Analysis failed during sleep metrics.",
                email="researcher@example.com",
                file_name="recording.gt3x",
                request_id="request-123",
                configuration={"activityMapping": "pim", "analysisScope": "family"},
                selected_files=[{"name": "recording.gt3x", "sizeMb": 12.5}],
                recent_errors=[{"area": "activity_analysis", "message": "example error"}],
            )
            response = asyncio.run(submit_feedback(payload))
            self.assertTrue(response["ok"])

            feedback_path = os.path.join(directory, "feedback.jsonl")
            with open(feedback_path, "r", encoding="utf-8") as handle:
                stored = json.loads(handle.readline())
            self.assertEqual(stored["request_id"], "request-123")
            self.assertEqual(stored["configuration"]["activityMapping"], "pim")
            self.assertEqual(stored["selected_files"][0]["name"], "recording.gt3x")
            self.assertTrue(stored["id"])
            self.assertTrue(stored["created_at"].endswith("+00:00"))

            listing = asyncio.run(list_feedback(_request("test-admin-secret"), limit=100))
            self.assertEqual(listing["matching_count"], 1)
            self.assertEqual(listing["records"][0]["file_name"], "recording.gt3x")
            self.assertFalse(listing["storage_persistent"])

            export = asyncio.run(export_feedback(_request("test-admin-secret"), format="csv"))
            rows = list(csv.DictReader(io.StringIO(export.body.decode("utf-8"))))
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["request_id"], "request-123")
            self.assertIn('"activityMapping": "pim"', rows[0]["configuration"])

    def test_feedback_search_filters_complete_record(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(
            os.environ,
            {"APP_DATA_DIR": directory, "FEEDBACK_ADMIN_TOKEN": "test-admin-secret"},
            clear=False,
        ):
            asyncio.run(submit_feedback(FeedbackPayload(message="First", email="first@example.com", configuration={"activityMapping": "zcm"})))
            asyncio.run(submit_feedback(FeedbackPayload(message="Second", email="second@example.com", configuration={"activityMapping": "mad"})))

            listing = asyncio.run(
                list_feedback(_request("test-admin-secret"), limit=100, search="zcm")
            )
            self.assertEqual(listing["matching_count"], 1)
            self.assertEqual(listing["records"][0]["message"], "First")

    def test_feedback_requires_a_valid_contact_email(self):
        with self.assertRaises(ValidationError):
            FeedbackPayload(message="Missing contact email")

        with tempfile.TemporaryDirectory() as directory, patch.dict(
            os.environ,
            {"APP_DATA_DIR": directory},
            clear=False,
        ):
            with self.assertRaises(HTTPException) as raised:
                asyncio.run(submit_feedback(FeedbackPayload(message="Please contact me.", email="not-an-email")))
            self.assertEqual(raised.exception.status_code, 422)
            self.assertIn("valid email address", raised.exception.detail)
            self.assertFalse(os.path.exists(os.path.join(directory, "feedback.jsonl")))

    def test_feedback_older_than_30_days_is_removed(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(
            os.environ,
            {"APP_DATA_DIR": directory, "FEEDBACK_ADMIN_TOKEN": "test-admin-secret"},
            clear=False,
        ):
            now = datetime.now(timezone.utc)
            old_record = {
                "id": "old-feedback",
                "created_at": (now - timedelta(days=31)).isoformat(),
                "category": "issue",
                "message": "Expired report",
                "email": "old@example.com",
            }
            recent_record = {
                "id": "recent-feedback",
                "created_at": (now - timedelta(days=29)).isoformat(),
                "category": "suggestion",
                "message": "Current report",
                "email": "recent@example.com",
            }
            feedback_path = os.path.join(directory, "feedback.jsonl")
            with open(feedback_path, "w", encoding="utf-8") as handle:
                handle.write(json.dumps(old_record) + "\n")
                handle.write(json.dumps(recent_record) + "\n")

            listing = asyncio.run(list_feedback(_request("test-admin-secret"), limit=100))
            self.assertEqual(listing["retention_days"], 30)
            self.assertEqual(listing["matching_count"], 1)
            self.assertEqual(listing["records"][0]["id"], "recent-feedback")

            with open(feedback_path, "r", encoding="utf-8") as handle:
                retained = [json.loads(line) for line in handle if line.strip()]
            self.assertEqual([item["id"] for item in retained], ["recent-feedback"])


if __name__ == "__main__":
    unittest.main()
