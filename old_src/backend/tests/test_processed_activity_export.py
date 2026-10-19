"""Preprocessed time-series CSV and manifest must match final analysis QC."""
import csv
import io
import json
import tempfile
import sys
import types
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

import pandas as pd
from fastapi import UploadFile
from fastapi.testclient import TestClient
import os
import time

try:
    import pyActigraphy  # noqa: F401
except ImportError:
    mock = types.ModuleType("pyActigraphy")
    mock_io = types.ModuleType("pyActigraphy.io")
    mock_io.BaseRaw = type("_TestBaseRaw", (), {})
    mock.io = mock_io
    sys.modules["pyActigraphy"] = mock
    sys.modules["pyActigraphy.io"] = mock_io

from backend.data_quality import apply_data_quality_control
from backend.processed_activity_export import write_processed_activity_archive
from backend.app import app, _background_processed_activity_export_worker
from backend.tests.test_raw_signal_geneactiv_integration import create_demo_bin


class ProcessedActivityExportTests(unittest.TestCase):
    def test_export_preserves_processed_values_gaps_manual_mask_and_selected_scope(self):
        index = pd.date_range("2026-01-01", periods=4, freq="30min")
        raw = types.SimpleNamespace(
            data=pd.Series([1.1, 2.2, float("nan"), 3.3], index=index),
            frequency=pd.Timedelta(minutes=30),
            _ui_mask_intervals=[{"start": index[1].isoformat(), "stop": (index[1] + pd.Timedelta(minutes=5)).isoformat()}],
        )
        config = {
            "supportFileSettings": {"masking": {"customizeDataQualityThresholds": True, "minimumValidHoursPerDay": 1}},
            "analysisWindowSettings": {"mode": "selected", "manualIntervals": [
                {"start": index[1].isoformat(), "stop": index[3].isoformat()},
            ]},
        }
        cleaned, quality = apply_data_quality_control(raw, config["supportFileSettings"])
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / "processed_activity.zip"
            write_processed_activity_archive(
                destination, raw, cleaned, source_names=["participant.bin"],
                mapping_details={"units": "g", "resolved": "accelerometer"}, signal_settings={"rawSignal": {"enabled": True}},
                analysis_config=config, data_quality=quality,
                support_summary={}, processing_provenance={"methods_text": "Test run"},
            )
            with zipfile.ZipFile(destination) as archive:
                rows = list(csv.DictReader(io.TextIOWrapper(archive.open("preprocessed_activity.csv"))))
                manifest = json.loads(archive.read("processing_manifest.json"))
        self.assertEqual(len(rows), 4)
        self.assertEqual([r["processed_activity_pre_qc"] for r in rows], ["1.1", "2.2", "", "3.3"])
        self.assertEqual([r["activity_used_for_analysis"] for r in rows], ["", "", "", "3.3"])
        self.assertEqual([r["recorded"] for r in rows], ["1", "1", "0", "1"])
        self.assertEqual([r["manually_masked"] for r in rows], ["0", "1", "0", "0"])
        self.assertEqual([r["within_selected_interval"] for r in rows], ["0", "1", "1", "1"])
        self.assertEqual(manifest["unit"], "g")
        self.assertEqual(manifest["raw_signal_processing_settings"]["rawSignal"]["enabled"], True)
        self.assertEqual(manifest["data_quality"]["valid_days"], 1)
        self.assertIn("manual_mask", rows[1]["exclusion_reason"])
        self.assertIn("recording_gap_or_missing", rows[2]["exclusion_reason"])

    def test_native_worker_regenerates_custom_signal_from_original_bin(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "demo.bin"
            create_demo_bin(source)
            # The app uses a 30-second analysis epoch. Build a 90-second fixture
            # from 45 native 2-second pages so the export has multiple epochs.
            fixture_lines = source.read_text().splitlines()
            header, sample_hex = fixture_lines[:3], fixture_lines[6]
            extended = list(header)
            for page in range(45):
                second = 2 * page
                extended.extend([
                    "Recorded Data",
                    f"Page Time: 2026-01-01 00:{second // 60:02d}:{second % 60:02d}:000",
                    "Measurement Frequency: 30", sample_hex,
                ])
            source.write_text("\n".join(extended))
            output = Path(directory) / "processed_activity.zip"
            upload = {"path": str(source), "filename": "demo.bin", "content_type": "application/octet-stream"}
            settings = {"rawSignal": {"enabled": True, "normalization": "positive_deviation", "output_unit": "g"}}
            with patch("backend.io_helpers.looks_like_geneactiv_bin", return_value=True):
                outcome = _background_processed_activity_export_worker(
                    upload, [], {"masking": [], "sleep_diary": [], "start_stop": []},
                    {"activityMapping": "accelerometer", "activitySignalSettings": json.dumps(settings),
                     "analysisConfig": "{}", "csvMapping": "{}", "csvSeparator": ",", "sourceFileName": "demo.bin"},
                    output, "testjob0001",
                )
            self.assertEqual(outcome["http_status"], 200, outcome)
            with zipfile.ZipFile(output) as archive:
                rows = list(csv.DictReader(io.TextIOWrapper(archive.open("preprocessed_activity.csv"))))
                manifest = json.loads(archive.read("processing_manifest.json"))
            self.assertEqual(len(rows), 3)
            for row in rows:
                self.assertAlmostEqual(float(row["processed_activity_pre_qc"]), 0.05, places=6)
                self.assertEqual(row["unit"], "g")
            self.assertTrue(manifest["processing_provenance"]["custom_raw_signal_processing"])

    def test_background_route_queues_and_serves_zip(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "fixture.bin"
            create_demo_bin(source)
            lines = source.read_text().splitlines()
            data = lines[6]
            all_lines = list(lines[:3])
            for page in range(45):
                second = page * 2
                all_lines.extend(["Recorded Data", f"Page Time: 2026-01-01 00:{second // 60:02d}:{second % 60:02d}:000", "Measurement Frequency: 30", data])
            source.write_text("\n".join(all_lines))
            with patch.dict(os.environ, {"APP_DATA_DIR": directory}), patch("backend.io_helpers.looks_like_geneactiv_bin", return_value=True):
                with TestClient(app) as client:
                    response = client.post("/api/jobs/export/processed-activity", files={"file": ("fixture.bin", source.read_bytes(), "application/octet-stream")}, data={
                        "activityMapping": "accelerometer", "activitySignalSettings": json.dumps({"rawSignal": {"enabled": True, "output_unit": "g", "normalization": "positive_deviation"}}),
                        "analysisConfig": "{}", "requestId": "testexportjob1234", "jobId": "testexportjob1234",
                    })
                    self.assertEqual(response.status_code, 202, response.text)
                    job_id = response.json()["job_id"]
                    latest = {}
                    for _ in range(70):
                        latest = client.get(f"/api/jobs/{job_id}").json()
                        if latest.get("status") in {"completed", "failed"}:
                            break
                        time.sleep(0.05)
                    self.assertEqual(latest.get("status"), "completed", latest)
                    self.assertIn("download_url", latest["result"])
                    binary = client.get(f"/api/jobs/{job_id}/download")
                    self.assertEqual(binary.status_code, 200, binary.text[:150] if binary.status_code != 200 else "")
                    self.assertEqual(binary.headers["content-type"], "application/zip")
                    with zipfile.ZipFile(io.BytesIO(binary.content)) as archive:
                        values = list(csv.DictReader(io.TextIOWrapper(archive.open("preprocessed_activity.csv"))))
                    self.assertEqual(len(values), 3)
                    self.assertEqual(values[0]["unit"], "g")


if __name__ == "__main__":
    unittest.main()
