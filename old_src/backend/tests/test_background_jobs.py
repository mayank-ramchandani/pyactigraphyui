import os
import json
import tempfile
import time
import unittest
from unittest.mock import patch

import numpy as np
import pandas as pd

from backend.analysis import build_native_preview
from backend.job_manager import create_job_record, get_job, get_job_result, submit_job


class BackgroundJobTests(unittest.TestCase):
    def _wait(self, job_id, timeout=5):
        deadline = time.time() + timeout
        while time.time() < deadline:
            record = get_job(job_id)
            if record and record.get("status") in {"completed", "failed"}:
                return record
            time.sleep(0.02)
        self.fail(f"Job {job_id} did not finish within {timeout} seconds")

    def test_job_persists_result_and_removes_input_payload(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(
            os.environ, {"APP_DATA_DIR": directory}, clear=False
        ):
            job_id, job_dir = create_job_record(
                "test", requested_job_id="job-test-1234", source_file_name="recording.gt3x"
            )
            input_path = job_dir / "inputs" / "recording.gt3x"
            input_path.write_bytes(b"test input")

            submit_job(job_id, lambda: {"http_status": 200, "content": {"answer": 42}})
            record = self._wait(job_id)
            result = get_job_result(job_id)

            self.assertEqual(record["status"], "completed")
            self.assertTrue(record["result_available"])
            self.assertEqual(result, {"http_status": 200, "content": {"answer": 42}})
            self.assertFalse((job_dir / "inputs").exists())

    def test_endpoint_error_becomes_failed_job_with_original_payload(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(
            os.environ, {"APP_DATA_DIR": directory}, clear=False
        ):
            job_id, _ = create_job_record("test", requested_job_id="job-test-5678")
            submit_job(
                job_id,
                lambda: {"http_status": 400, "content": {"detail": "bad recording"}},
            )
            record = self._wait(job_id)
            result = get_job_result(job_id)

            self.assertEqual(record["status"], "failed")
            self.assertEqual(record["result_http_status"], 400)
            self.assertEqual(result["content"]["detail"], "bad recording")

    def test_gapped_preview_and_job_result_are_strict_json(self):
        class Raw:
            format = "test"

        raw = Raw()
        raw.data = pd.Series(
            [1.0, np.inf, 3.0],
            index=pd.to_datetime(
                ["2020-01-01 00:00:00", "2020-01-01 00:01:00", "2020-01-01 00:03:00"]
            ),
            name="activity",
        )
        preview = build_native_preview(raw, activity_channel="activity", resample_freq="1min")

        # The missing 00:02 resample bin and the non-finite source value must
        # become JSON null rather than the non-standard NaN/Infinity tokens.
        json.dumps(preview, allow_nan=False)
        values = [point["activity"] for point in preview["full_recording_preview"]]
        self.assertEqual(values, [1.0, None, None, 3.0])

        with tempfile.TemporaryDirectory() as directory, patch.dict(
            os.environ, {"APP_DATA_DIR": directory}, clear=False
        ):
            job_id, _ = create_job_record("test", requested_job_id="job-test-strict-json")
            submit_job(
                job_id,
                lambda: {"http_status": 200, "content": {"preview_value": float("nan")}},
            )
            record = self._wait(job_id)
            result = get_job_result(job_id)

            self.assertEqual(record["status"], "completed")
            self.assertIsNone(result["content"]["preview_value"])


if __name__ == "__main__":
    unittest.main()
