import io
import os
import json
import tempfile
import time
import sys
import types
import unittest
from unittest.mock import patch

import numpy as np
import pandas as pd
from fastapi import UploadFile

from backend.analysis import build_native_preview, run_basic_pylight_analysis

# Route tests do not exercise native pyActigraphy readers. Keep them runnable
# in a lightweight test environment where the optional scientific stack is not
# installed; deployment tests still install the pinned requirements.
try:
    import pyActigraphy  # noqa: F401
except Exception:
    for module_name in list(sys.modules):
        if module_name == "pyActigraphy" or module_name.startswith("pyActigraphy."):
            sys.modules.pop(module_name, None)
    pyactigraphy_module = types.ModuleType("pyActigraphy")
    pyactigraphy_io_module = types.ModuleType("pyActigraphy.io")

    class _TestBaseRaw:
        pass

    pyactigraphy_io_module.BaseRaw = _TestBaseRaw
    pyactigraphy_module.io = pyactigraphy_io_module
    sys.modules["pyActigraphy"] = pyactigraphy_module
    sys.modules["pyActigraphy.io"] = pyactigraphy_io_module

from backend.app import (
    NO_LIGHT_MEASUREMENTS_DETAIL,
    analyze_light_batch,
    preview_light,
    start_background_light_analysis,
    start_background_light_preview,
)
from backend.geneactiv_bin import SimpleLightRecording
from backend.job_manager import (
    create_job_record,
    get_job,
    get_job_result,
    job_runtime_info,
    submit_job,
)


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

    def test_runtime_info_identifies_replica_revision_and_storage_scope(self):
        with patch.dict(
            os.environ,
            {
                "APP_DATA_DIR": "/data/actigraphy-ui",
                "CONTAINER_APP_REPLICA_NAME": "backend--rev-a-abc123",
                "CONTAINER_APP_REVISION": "backend--rev-a",
            },
            clear=False,
        ):
            runtime = job_runtime_info()

        self.assertEqual(runtime["replica"], "backend--rev-a-abc123")
        self.assertEqual(runtime["revision"], "backend--rev-a")
        self.assertTrue(runtime["persistent_data_dir_configured"])
        self.assertEqual(runtime["job_store_scope"], "configured_path")

    def test_gt3x_without_lux_returns_successful_explicit_skip(self):
        upload = UploadFile(
            file=io.BytesIO(b"fixture"),
            filename="large-recording.gt3x",
        )
        light = SimpleLightRecording({})
        raw = types.SimpleNamespace(
            format="ActiGraph GT3X (streaming lux)",
            metadata={
                "direct_gt3x_light_reader": True,
                "light_channels": {},
                "gt3x_summary": {
                    "_gt3x_light_inspected": True,
                    "_gt3x_light_available": False,
                    "_gt3x_lux_records": 0,
                    "_gt3x_light_events_read": 100,
                },
            },
            light=light,
            white_light=None,
            amb_light=None,
        )
        with patch(
            "backend.app._load_native_supported_file",
            return_value=(raw, "gt3x"),
        ):
            response = preview_light(
                file=upload,
                resampleFreq="1min",
                rgbResampleFreq="5min",
                csvMapping="{}",
                csvSeparator=",",
                maskingFiles=None,
                sleepDiaryFiles=None,
                startStopFiles=None,
            )

        self.assertEqual(response.status_code, 200)
        payload = json.loads(response.body)
        self.assertFalse(payload["light_preview_available"])
        self.assertTrue(payload["skipped"])
        self.assertFalse(payload["light_detection"]["available"])
        self.assertEqual(payload["message"], NO_LIGHT_MEASUREMENTS_DETAIL)

    def test_gt3x_background_light_job_is_accepted_for_content_inspection(self):
        upload = UploadFile(
            file=io.BytesIO(b"small gt3x fixture"),
            filename="large-recording.gt3x",
        )
        expected = {
            "http_status": 200,
            "content": {
                "light_preview_available": False,
                "skipped": True,
                "message": NO_LIGHT_MEASUREMENTS_DETAIL,
            },
        }
        with tempfile.TemporaryDirectory() as directory, patch.dict(
            os.environ, {"APP_DATA_DIR": directory}, clear=False
        ), patch("backend.app._background_light_worker", return_value=expected):
            response = start_background_light_preview(
                file=upload,
                resampleFreq="1min",
                rgbResampleFreq="5min",
                csvMapping="{}",
                csvSeparator=",",
                jobId="job-gt3x-light-inspect",
            )

            self.assertEqual(response.status_code, 202)
            job_id = json.loads(response.body)["job_id"]
            record = self._wait(job_id)
            result = get_job_result(job_id)

        self.assertEqual(record["status"], "completed")
        self.assertEqual(result, expected)

    def test_supported_light_preview_uses_background_job_lifecycle(self):
        upload = UploadFile(
            file=io.BytesIO(b"small supported fixture"),
            filename="recording.bin",
        )
        expected = {
            "http_status": 200,
            "content": {
                "light_preview_available": True,
                "channels": ["LIGHT", "LIGHT_LUX"],
            },
        }

        with tempfile.TemporaryDirectory() as directory, patch.dict(
            os.environ, {"APP_DATA_DIR": directory}, clear=False
        ), patch("backend.app._background_light_worker", return_value=expected):
            response = start_background_light_preview(
                file=upload,
                resampleFreq="1min",
                rgbResampleFreq="5min",
                csvMapping="{}",
                csvSeparator=",",
                jobId="job-light-preview-supported",
            )
            self.assertEqual(response.status_code, 202)
            job_id = json.loads(response.body)["job_id"]
            record = self._wait(job_id)
            result = get_job_result(job_id)

            self.assertEqual(record["job_type"], "light_preview")
            self.assertEqual(record["status"], "completed")
            self.assertEqual(result, expected)
            self.assertFalse(os.path.exists(os.path.join(directory, "jobs", job_id, "inputs")))

    def test_light_analysis_batch_uses_one_background_job(self):
        upload = UploadFile(
            file=io.BytesIO(b"small supported fixture"),
            filename="recording.gt3x",
        )
        expected = {
            "http_status": 200,
            "content": {
                "light_available": True,
                "results": {
                    "tat": {"metric_id": "tat"},
                    "iv": {"metric_id": "iv"},
                },
            },
        }

        with tempfile.TemporaryDirectory() as directory, patch.dict(
            os.environ, {"APP_DATA_DIR": directory}, clear=False
        ), patch("backend.app._background_light_worker", return_value=expected):
            response = start_background_light_analysis(
                file=upload,
                metricIds='["tat","iv"]',
                channel="LIGHT",
                thresholdLux="100",
                startTime="",
                stopTime="",
                bins="24h",
                agg="mean",
                aggFuncs="mean,median",
                outputFormat="minute",
                lmxLength="5h",
                lowest="true",
                binarize="false",
                requestId="job-light-analysis-batch",
                jobId="job-light-analysis-batch",
            )
            self.assertEqual(response.status_code, 202)
            job_id = json.loads(response.body)["job_id"]
            record = self._wait(job_id)
            result = get_job_result(job_id)

        self.assertEqual(record["job_type"], "light_analyze")
        self.assertEqual(record["status"], "completed")
        self.assertEqual(result, expected)

    def test_light_analysis_batch_skips_all_metrics_when_inspection_finds_no_light(self):
        upload = UploadFile(file=io.BytesIO(b"fixture"), filename="recording.gt3x")
        raw = types.SimpleNamespace(
            format="ActiGraph GT3X (streaming lux)",
            metadata={
                "direct_gt3x_light_reader": True,
                "light_channels": {},
                "gt3x_summary": {
                    "_gt3x_light_inspected": True,
                    "_gt3x_light_available": False,
                    "_gt3x_lux_records": 0,
                },
            },
            data=pd.Series(dtype=float),
            light=SimpleLightRecording({}),
        )

        with patch("backend.app.load_native_file", return_value=raw) as load_recording, patch(
            "backend.app.run_basic_pylight_analysis",
            side_effect=AssertionError("Metrics must not run when no light data exist"),
        ):
            response = analyze_light_batch(
                file=upload,
                metricIds='["tat","iv"]',
                channel="",
                thresholdLux="100",
                startTime="",
                stopTime="",
                bins="24h",
                agg="mean",
                aggFuncs="mean,median",
                outputFormat="minute",
                lmxLength="5h",
                lowest="true",
                binarize="false",
                requestId="job-no-light-batch",
            )

        payload = json.loads(response.body)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(payload["skipped"])
        self.assertEqual(payload["results"], {})
        self.assertEqual(payload["metric_diagnostics"]["tat"]["status"], "skipped")
        self.assertEqual(payload["metric_diagnostics"]["iv"]["status"], "skipped")
        load_recording.assert_called_once()

    def test_lux_threshold_is_converted_for_each_selected_channel_scale(self):
        index = pd.date_range("2026-01-01", periods=2, freq="1min")
        raw_lux = pd.Series([0.0, 100.0], index=index, name="LIGHT_LUX")
        light = SimpleLightRecording(
            {
                "LIGHT": np.log10(raw_lux + 1.0).rename("LIGHT"),
                "LIGHT_LUX": raw_lux,
            }
        )
        raw = types.SimpleNamespace(
            metadata={
                "direct_gt3x_light_reader": True,
                "light_channels": {
                    "LIGHT": "log10(lux + 1)",
                    "LIGHT_LUX": "lux",
                },
            },
            light=light,
        )

        log_payload = run_basic_pylight_analysis(
            raw, metric_id="tat", channel="LIGHT", threshold_lux="10"
        )
        lux_payload = run_basic_pylight_analysis(
            raw, metric_id="tat", channel="LIGHT_LUX", threshold_lux="10"
        )

        self.assertEqual(log_payload["threshold_channel_scale"], "log10(lux + 1)")
        self.assertAlmostEqual(log_payload["threshold_channel_value"], np.log10(11), places=2)
        self.assertEqual(lux_payload["threshold_channel_scale"], "lux")
        self.assertEqual(lux_payload["threshold_channel_value"], 10.0)

    def test_light_preview_returns_plot_channels_and_rgb_from_one_loaded_recording(self):
        index = pd.date_range("2026-01-01", periods=12, freq="1min")
        light = SimpleLightRecording(
            {
                "LIGHT": pd.Series(np.linspace(0.0, 2.0, len(index)), index=index, name="LIGHT"),
                "LIGHT_LUX": pd.Series(np.linspace(0.0, 99.0, len(index)), index=index, name="LIGHT_LUX"),
            }
        )
        raw = types.SimpleNamespace(
            format="GENEActiv BIN",
            metadata={
                "direct_geneactiv_reader": True,
                "light_channels": {
                    "LIGHT": "log10(lux + 1)",
                    "LIGHT_LUX": "lux",
                },
            },
            light=light,
            white_light=light.get_channel("LIGHT"),
            amb_light=light.get_channel("LIGHT"),
        )
        upload = UploadFile(file=io.BytesIO(b"fixture"), filename="recording.bin")

        with patch(
            "backend.app._load_native_supported_file",
            return_value=(raw, "geneactiv_bin_accelerometer"),
        ) as load_recording:
            response = preview_light(
                file=upload,
                resampleFreq="1min",
                rgbResampleFreq="5min",
                csvMapping="{}",
                csvSeparator=",",
                maskingFiles=None,
                sleepDiaryFiles=None,
                startStopFiles=None,
            )

        payload = json.loads(response.body)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(payload["light_preview_available"])
        self.assertEqual(payload["channels"], ["LIGHT", "LIGHT_LUX"])
        self.assertEqual(payload["default_channel"], "LIGHT")
        self.assertGreater(len(payload["light_preview"]), 0)
        self.assertGreater(len(payload["rgb_preview"]), 0)
        self.assertEqual(payload["rgb_resample_freq"], "5min")
        load_recording.assert_called_once()


if __name__ == "__main__":
    unittest.main()
