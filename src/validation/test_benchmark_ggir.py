"""Pure, fast tests for benchmark CSV handling; no server or R needed."""
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

import pandas as pd

from validation.benchmark_ggir import qc_rows, find_ggir_outputs, paired_summary_metrics, paired_daily_coverage


class BenchmarkTests(TestCase):
    def test_qc_export_missing_nonwear_and_16_hours(self):
        sample = {"detected_nonwear_available": False, "modes": {"calendar_day": {"windows": [
            {"date": "2026-01-01", "recorded_hours": 17, "analyzable_hours": 17,
             "recording_gap_hours": 7, "detected_nonwear_hours": 0},
            {"date": "2026-01-02", "recorded_hours": 15.99, "analyzable_hours": 15.99,
             "recording_gap_hours": 8.01, "detected_nonwear_hours": 0},
        ]}}}
        rows = qc_rows(sample, "calendar_day", 16, True, "anonymous.bin")
        self.assertEqual([row["valid_16h"] for row in rows], [True, False])
        self.assertIsNone(rows[0]["detected_nonwear_hours"])

    def test_ggir_manifest_with_mock_part2_files(self):
        with TemporaryDirectory() as temp:
            root = Path(temp) / "ggir"
            output = Path(temp) / "results"
            (root / "results" / "QC").mkdir(parents=True)
            output.mkdir()
            pd.DataFrame([{"filename": "anonymous.bin", "meas_dur_dys": 2}]).to_csv(root / "results" / "part2_summary.csv", index=False)
            pd.DataFrame([{"file.corrupt": False}]).to_csv(root / "results" / "QC" / "data_quality_report.csv", index=False)
            manifest = find_ggir_outputs(root, output)
            self.assertEqual(manifest["ggir_part2_summary"]["status"], "present")
            self.assertTrue((output / "ggir_file_quality.csv").exists())
            self.assertEqual(manifest["ggir_part2_daysummary"]["status"], "not_found")

    def test_metric_summary_comparison_only_user_selected(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            a, g, out = [root / x for x in ("a.csv", "g.csv", "pairs.csv")]
            pd.DataFrame([{"ra": 0.61}]).to_csv(a, index=False)
            pd.DataFrame([{"RAggir": 0.60}]).to_csv(g, index=False)
            paired_summary_metrics(a, g, "ra:RAggir", out)
            self.assertAlmostEqual(float(pd.read_csv(out).iloc[0]["actilab_minus_ggir"]), 0.01)
            self.assertFalse(bool(pd.read_csv(out).iloc[0]["comparable_methods_confirmed"]))

    def test_daily_comparison_join_by_date_with_missing_dates(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            a, g, out = [root / x for x in ("a.csv", "g.csv", "daily.csv")]
            pd.DataFrame([{"date": "2026-01-01", "hours_used_for_validity": 17},
                          {"date": "2026-01-02", "hours_used_for_validity": 20}]).to_csv(a, index=False)
            pd.DataFrame([{"date_g": "2026-01-02", "hours_g": 19}]).to_csv(g, index=False)
            paired_daily_coverage(a, g, "date_g", "hours_g", out)
            df = pd.read_csv(out)
            self.assertEqual(len(df), 2)
            self.assertEqual(float(df.loc[df["date"] == "2026-01-02", "actilab_minus_ggir_hours"].iloc[0]), 1)
