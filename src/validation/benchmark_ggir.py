#!/usr/bin/env python3
"""Benchmark ActiLab Step 2 QC + full analysis alongside GGIR Part 1/2 (optional 3-5).

Requires: pip install requests pandas. GGIR requires R + install.packages('GGIR').
No clinical data leaves the specified ActiLab server (choose localhost for local runs).
These are DIFFERENT pipeline stages, so timings and numbers are descriptive, not parity proof.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import pandas as pd
import requests

DEFAULT_ANALYSIS = {
    "analysisScope": "metric",
    "metrics": [
        {"id": "ra", "params": {"binarize": False}},
        {"id": "is", "params": {"binarize": False}},
        {"id": "iv", "params": {"binarize": False}},
    ],
    "families": [],
    "algorithm": None,  # Sleep is intentionally out of scope in the default benchmark.
    "analysisWindowSettings": {"mode": "full"},
    "sleepWindowSettings": {"estimateWithoutDiary": False},
    "supportFileSettings": {
        "startStop": {"apply": False, "manualIntervals": []},
        "masking": {
            "apply": True, "manualIntervals": [], "respectNonwear": True,
            "customizeDataQualityThresholds": True,
            "validDayWindowMode": "calendar_day", "minimumValidHoursPerDay": 16,
            "minimumValidDaysForRhythm": 2, "minimumSleepWindowCoverage": 0.8,
        },
        "sleepDiary": {"apply": False, "manualIntervals": []},
    },
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def http_stage(base: str, route: str, file: Path, fields: dict[str, str],
               timeout: int, async_jobs: bool, poll_seconds: float) -> tuple[dict, float]:
    """Times upload, queue time, and processing through result retrieval; not CPU time."""
    start = time.perf_counter()
    endpoint = f"{base.rstrip('/')}/api/{'jobs/' if async_jobs else ''}{route}"
    job_id = None
    with file.open("rb") as stream:
        response = requests.post(endpoint, files={"file": (file.name, stream, "application/octet-stream")},
                                 data=fields, timeout=timeout)
    try:
        result = response.json()
    except ValueError as error:
        raise RuntimeError(f"Non-JSON response ({response.status_code}) from {endpoint}: {response.text[:500]}") from error
    if response.status_code >= 400:
        raise RuntimeError(f"ActiLab request failed ({response.status_code}): {result.get('detail', result)}")
    if async_jobs:
        job_id = result.get("job_id")
        if not job_id:
            raise RuntimeError(f"No job_id returned by {endpoint}: {result}")
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            time.sleep(poll_seconds)
            response = requests.get(f"{base.rstrip('/')}/api/jobs/{job_id}", timeout=60)
            if response.status_code == 404:
                # A transient 404 is possible on an unshared multi-replica deployment.
                continue
            response.raise_for_status()
            job = response.json()
            if job.get("status") in {"failed", "completed"}:
                result = job.get("result") or {}
                code = int(job.get("result_http_status") or (500 if job.get("status") == "failed" else 200))
                if code >= 400 or job.get("status") == "failed":
                    raise RuntimeError(f"ActiLab job {job_id} failed: {result.get('detail') or job.get('message')}")
                return result, time.perf_counter() - start
        raise TimeoutError(f"ActiLab job {job_id} did not finish within {timeout} seconds")
    return result, time.perf_counter() - start


def qc_rows(payload: dict, mode: str, min_hours: float, respect_nonwear: bool, input_file: str) -> list[dict]:
    rows = []
    for item in payload.get("modes", {}).get(mode, {}).get("windows", []):
        used = item.get("analyzable_hours") if respect_nonwear else item.get("recorded_hours")
        hours = float(used or 0)
        rows.append({
            "source_file": input_file, "date": item.get("date"),
            "window_start": item.get("window_start"), "window_stop": item.get("window_stop"),
            "window_mode": mode, "recorded_hours": item.get("recorded_hours"),
            "recording_gap_hours": item.get("recording_gap_hours"),
            "detected_nonwear_available": payload.get("detected_nonwear_available", False),
            "detected_nonwear_hours": item.get("detected_nonwear_hours") if payload.get("detected_nonwear_available") else None,
            "analyzable_hours": item.get("analyzable_hours"),
            "hours_used_for_validity": hours, "valid_16h": bool(hours + 1e-9 >= min_hours),
            "minimum_valid_hours": min_hours,
        })
    return rows


def find_ggir_outputs(root: Path, output: Path) -> dict[str, Any]:
    patterns = {
        "ggir_part2_summary": "part2_summary.csv",
        "ggir_part2_daysummary": "part2_daysummary.csv",
        "ggir_file_quality": "data_quality_report.csv",
    }
    manifest = {}
    for label, name in patterns.items():
        matches = sorted(root.rglob(name))
        if not matches:
            manifest[label] = {"status": "not_found", "pattern": name}
            continue
        target = matches[0]
        table = pd.read_csv(target, low_memory=False)
        table.to_csv(output / f"{label}.csv", index=False)
        manifest[label] = {"status": "present", "source": str(target), "columns": list(table.columns), "rows": len(table)}
    return manifest


def compare_recording_overview(qc_payload: dict, ggir_dir: Path, outdir: Path) -> None:
    """Only show duration side-by-side. The quality definitions are not matched."""
    file_summary = outdir / "ggir_part2_summary.csv"
    if not file_summary.exists():
        return
    ggir = pd.read_csv(file_summary)
    first = ggir.iloc[0] if len(ggir) == 1 else None
    duration = float(qc_payload.get("timeline_hours", 0))
    data = [{"measurement": "recording_span_hours", "actilab": duration,
             "ggir": float(first["meas_dur_dys"]) * 24 if first is not None and "meas_dur_dys" in ggir and pd.notna(first["meas_dur_dys"]) else None,
             "scientifically_equivalent": False,
             "note": "GGIR measurement-duration and ActiLab timestamp span may use different endpoint/protocol definitions."},
            {"measurement": "recorded_hours", "actilab": qc_payload.get("recorded_hours"),
             "ggir": None, "scientifically_equivalent": False,
             "note": "GGIR Part 2 uses raw calibration/non-wear/masking; no direct recorded-epoch equivalent asserted."},
            {"measurement": "recording_gap_hours", "actilab": qc_payload.get("recording_gap_hours"),
             "ggir": None, "scientifically_equivalent": False,
             "note": "Missing timestamps are not equivalent to GGIR non-wear or imputed invalid epochs."}]
    pd.DataFrame(data).to_csv(outdir / "qc_overview_comparison.csv", index=False)


def paired_summary_metrics(actilab: Path, ggir: Path, metric_pairs: str, output: Path) -> None:
    """Explicit single-recording crosswalk; analyst must verify each definition."""
    a, g = pd.read_csv(actilab), pd.read_csv(ggir)
    if len(a) != 1 or len(g) != 1:
        raise ValueError("Summary comparison expects exactly one ActiLab and one GGIR recording")
    rows = []
    for chunk in metric_pairs.split(","):
        pair = chunk.strip().split(":", 1)
        if len(pair) != 2 or not all(pair):
            raise ValueError(f"Invalid metric pair {chunk!r}; expected actilab_column:ggir_column")
        left, right = pair
        if left not in a or right not in g:
            raise ValueError(f"Missing crosswalk column {left!r} or {right!r}. See GGIR output manifest and ActiLab aggregated CSV.")
        ax = pd.to_numeric(a.loc[0, left], errors="coerce")
        gx = pd.to_numeric(g.loc[0, right], errors="coerce")
        delta = float(ax - gx) if pd.notna(ax) and pd.notna(gx) else None
        rows.append({"actilab_column": left, "ggir_column": right,
                     "actilab_value": ax, "ggir_value": gx, "actilab_minus_ggir": delta,
                     "comparable_methods_confirmed": False,
                     "note": "Check units, activity basis, calibration, epoch, nonwear, date/time and masking before interpreting delta."})
    pd.DataFrame(rows).to_csv(output, index=False)


def paired_daily_coverage(actilab_qc: Path, ggir_day: Path, date_column: str,
                          hours_column: str, output: Path) -> None:
    """Align on calendar dates only after the analyst supplies GGIR's actual columns."""
    a, g = pd.read_csv(actilab_qc), pd.read_csv(ggir_day)
    if date_column not in g or hours_column not in g:
        raise ValueError(f"GGIR missing chosen date/hours column: {date_column!r}, {hours_column!r}")
    a = a.copy()
    g = g.copy()
    a["_date"] = pd.to_datetime(a["date"], errors="coerce").dt.date
    g["_date"] = pd.to_datetime(g[date_column], errors="coerce").dt.date
    if a["_date"].isna().any() or g["_date"].isna().any():
        raise ValueError("Some dates cannot be parsed; supply a GGIR calendar-date column, not a day number")
    if a["_date"].duplicated().any() or g["_date"].duplicated().any():
        raise ValueError("Multiple rows per calendar date; filter GGIR to one recording/day before comparison")
    left = a[["_date", "hours_used_for_validity"]].rename(columns={"hours_used_for_validity": "actilab_hours"})
    right = g[["_date", hours_column]].rename(columns={hours_column: "ggir_hours"})
    merged = left.merge(right, on="_date", how="outer", indicator=True)
    merged["ggir_hours"] = pd.to_numeric(merged["ggir_hours"], errors="coerce")
    merged["actilab_hours"] = pd.to_numeric(merged["actilab_hours"], errors="coerce")
    merged["actilab_minus_ggir_hours"] = merged["actilab_hours"] - merged["ggir_hours"]
    merged["method_equivalence_confirmed"] = False
    merged["note"] = "Values are only commensurate if GGIR column truly means recorded/analyzable hours under aligned definitions"
    merged.rename(columns={"_date": "date", "_merge": "record_presence"}).to_csv(output, index=False)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--file", type=Path, required=True, help="Single de-identified raw file; recommended .bin/.gt3x")
    parser.add_argument("--actilab-url", default="http://127.0.0.1:8000")
    parser.add_argument("--out", type=Path, default=Path("validation/benchmark_results"))
    parser.add_argument("--activity-mapping", default="enmo", choices=["auto", "accelerometer", "enmo", "mad", "pim", "zcm", "tat", "original"])
    parser.add_argument("--epoch", type=int, default=5, choices=[5, 10, 15, 30, 60])
    parser.add_argument("--analysis-config", type=Path, help="Optional JSON matching exported ActiLab analysis settings")
    parser.add_argument("--qc-only", action="store_true", help="Skip ActiLab full analysis")
    parser.add_argument("--sync", action="store_true", help="Use synchronous endpoints (not advised for large files)")
    parser.add_argument("--timeout", type=int, default=21600, help="Total wait per ActiLab stage, seconds")
    parser.add_argument("--poll", type=float, default=2.0)
    parser.add_argument("--run-ggir", action="store_true", help="Run GGIR via Rscript on this computer")
    parser.add_argument("--ggir-existing", type=Path, help="Use a prior GGIR output folder instead of running R")
    parser.add_argument("--ggir-parts", default="1,2", help="GGIR stages, e.g. 1,2 or 1,2,3,4,5")
    parser.add_argument("--summary-pairs", help="Explicit ActiLab:GGIR summary column pairs, e.g. inter_daily_stability:IS (verify actual names first)")
    parser.add_argument("--ggir-date-column", help="GGIR Part 2 day-summary calendar-date column for aligned daily QC")
    parser.add_argument("--ggir-hours-column", help="GGIR Part 2 day-summary hours column (must be comparable to ActiLab hours)")
    parser.add_argument("--timezone", default="UTC", help="GGIR desiredtz; also document the ActiLab file timezone")
    parser.add_argument("--ggir-calibrate", action=argparse.BooleanOptionalAction, default=True)
    args = parser.parse_args(argv)
    if not args.file.is_file():
        parser.error("--file must refer to an existing recording")
    if bool(args.ggir_date_column) != bool(args.ggir_hours_column):
        parser.error("Provide both --ggir-date-column and --ggir-hours-column")
    if args.run_ggir and args.ggir_existing:
        parser.error("Use --run-ggir OR --ggir-existing, not both")
    output = args.out.resolve()
    output.mkdir(parents=True, exist_ok=True)
    analysis_config = json.loads(args.analysis_config.read_text("utf-8")) if args.analysis_config else DEFAULT_ANALYSIS
    parameters = {"activityMapping": args.activity_mapping,
                  "activitySignalSettings": json.dumps({"epochSeconds": args.epoch}),
                  "csvMapping": "{}", "csvSeparator": ","}
    record = {
        "source_file": args.file.name, "size_bytes": args.file.stat().st_size,
        "sha256": sha256_file(args.file), "timezone_selected_for_ggir": args.timezone,
        "actilab_url": args.actilab_url, "activity_mapping": args.activity_mapping,
        "actilab_epoch_seconds": args.epoch, "ggir_short_epoch_seconds": 5,
        "ggir_calibration": args.ggir_calibrate,
        "timing_semantics": "ActiLab = upload + queue + analysis + HTTP polling; GGIR = R part invocation + disk IO; not hardware/network matched",
        "ggir_vs_actilab_status": "Exploratory descriptive comparison; not validated equivalent",
    }
    (output / "benchmark_config.json").write_text(json.dumps({**record, "analysis_config": analysis_config}, indent=2), encoding="utf-8")
    timing = []
    try:
        print("Running ActiLab initial QC…", flush=True)
        qc, seconds = http_stage(args.actilab_url, "qc/initial", args.file, parameters,
                                 args.timeout, not args.sync, args.poll)
        (output / "actilab_initial_qc.json").write_text(json.dumps(qc, indent=2), encoding="utf-8")
        pd.DataFrame(qc_rows(qc, "calendar_day", 16, True, args.file.name)).to_csv(output / "actilab_initial_qc.csv", index=False)
        timing.append({"tool": "ActiLab", "operation": "step2_initial_qc", "seconds": seconds, "success": True, "message": "HTTP end-to-end"})
        if not args.qc_only:
            print("Running ActiLab analysis (including final QC)…", flush=True)
            analysis, seconds = http_stage(args.actilab_url, "analyze/basic", args.file,
                                            {**parameters, "analysisMode": "custom", "analysisConfig": json.dumps(analysis_config)},
                                            args.timeout, not args.sync, args.poll)
            (output / "actilab_analysis.json").write_text(json.dumps(analysis, indent=2), encoding="utf-8")
            tables = analysis.get("release_tables") or {}
            pd.DataFrame(tables.get("daily_rows") or []).to_csv(output / "actilab_final_daily.csv", index=False)
            pd.DataFrame(tables.get("aggregated_rows") or []).to_csv(output / "actilab_aggregated.csv", index=False)
            (output / "actilab_final_qc.json").write_text(json.dumps(analysis.get("dataQuality") or {}, indent=2), encoding="utf-8")
            timing.append({"tool": "ActiLab", "operation": "full_analysis_and_final_qc", "seconds": seconds, "success": True, "message": "HTTP end-to-end"})
    except Exception as exc:
        timing.append({"tool": "ActiLab", "operation": "failed", "seconds": None, "success": False, "message": str(exc)})
        pd.DataFrame(timing).to_csv(output / "benchmark_timings.csv", index=False)
        raise

    ggir_root = None
    if args.run_ggir:
        ggir_root = output / "ggir_run"
        ggir_root.mkdir(exist_ok=True)
        command = ["Rscript", str(Path(__file__).with_name("run_ggir_benchmark.R")),
                   str(args.file.resolve()), str(ggir_root), args.ggir_parts,
                   args.timezone, str(args.ggir_calibrate).lower()]
        print("Running GGIR; output in", ggir_root, flush=True)
        started = time.perf_counter()
        with (output / "ggir_stdout.log").open("w", encoding="utf-8") as log:
            try:
                proc = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, check=False)
                success = proc.returncode == 0
                message = "" if success else f"Rscript returned {proc.returncode}; inspect ggir_stdout.log"
            except FileNotFoundError:
                success, message = False, "Rscript not found; install R and GGIR"
        timing.append({"tool": "GGIR", "operation": "invocation_all_requested_parts", "seconds": time.perf_counter() - started, "success": success, "message": message})
        part_csv = ggir_root / "ggir_timing.csv"
        if part_csv.exists():
            timing += pd.read_csv(part_csv).to_dict(orient="records")
        if not success:
            print("GGIR did not complete:", message, file=sys.stderr)
    elif args.ggir_existing:
        ggir_root = args.ggir_existing.resolve()

    if ggir_root and ggir_root.exists():
        manifest = find_ggir_outputs(ggir_root, output)
        (output / "ggir_output_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        compare_recording_overview(qc, ggir_root, output)
        if args.summary_pairs and (output / "actilab_aggregated.csv").exists() and (output / "ggir_part2_summary.csv").exists():
            paired_summary_metrics(output / "actilab_aggregated.csv", output / "ggir_part2_summary.csv",
                                   args.summary_pairs, output / "metric_pairs_summary.csv")
        if args.ggir_date_column and (output / "ggir_part2_daysummary.csv").exists():
            paired_daily_coverage(output / "actilab_initial_qc.csv", output / "ggir_part2_daysummary.csv",
                                  args.ggir_date_column, args.ggir_hours_column, output / "qc_daily_pairs.csv")
    pd.DataFrame(timing).to_csv(output / "benchmark_timings.csv", index=False)
    print(f"Wrote benchmark files to {output}")
    print("WARNING: Step 2 QC, final QC and GGIR Part 1/2 QC are not interchangeable; see GGIR_COMPARISON_PROTOCOL.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
