"""Reproducible, epoch-level export from the same QC activity series used in analysis.

The saved CSV contains the epoch representation (not original high-frequency XYZ),
pre-QC and usable analysis values, plus exclusion/interval flags.  It is written
incrementally to a ZIP so even long recordings do not require a giant JSON blob.
"""
from __future__ import annotations

import csv
from importlib import metadata as package_metadata
from datetime import datetime, timezone
import io
import json
from pathlib import Path
import zipfile

import numpy as np
import pandas as pd

from .analysis import _normalize_analysis_windows
from .data_quality import _manual_interval_mask, _reader_mask
from .diagnostics import make_json_safe

COLUMNS = [
    "timestamp", "processed_activity_pre_qc", "activity_used_for_analysis", "unit",
    "recorded", "detected_nonwear", "nonwear_exclusion_applied", "manually_masked",
    "excluded_by_quality_window", "within_selected_interval", "included_in_final_analysis",
    "exclusion_reason",
]


def processed_activity_rows(source_raw, analysis_raw, *, units, analysis_window_settings=None, data_quality=None):
    """Return an iterator of row tuples and its mode without modifying either raw."""
    series = getattr(analysis_raw, "_ui_source_activity_series", None)
    valid = getattr(analysis_raw, "_ui_analysis_valid_mask", None)
    if not isinstance(series, pd.Series) or not isinstance(valid, pd.Series):
        raise ValueError("Processed export requires completed, shared data-quality processing.")
    index = series.index
    valid = valid.reindex(index, fill_value=False).astype(bool).to_numpy()
    recorded = np.isfinite(pd.to_numeric(series, errors="coerce").to_numpy(dtype=float))
    settings = (data_quality or {}).get("settings") or {}
    native_mask = _reader_mask(source_raw, index)
    detected = (~native_mask.reindex(index, fill_value=True).astype(bool).to_numpy()) if native_mask is not None else np.zeros(len(index), dtype=bool)
    respect_nonwear = bool(settings.get("respect_detected_nonwear", True))
    manual_wear = _manual_interval_mask(index, getattr(source_raw, "_ui_mask_intervals", None) or []).to_numpy(dtype=bool)
    manual = ~manual_wear

    window_settings = analysis_window_settings or {}
    mode = window_settings.get("mode", "full")
    in_interval = np.zeros(len(index), dtype=bool)
    if mode in {"selected", "both"}:
        for window in _normalize_analysis_windows(window_settings, raw=analysis_raw):
            in_interval |= np.asarray((index >= window["start"]) & (index <= window["stop"]), dtype=bool)
    else:
        in_interval[:] = True
    accepted_scope = in_interval if mode == "selected" else np.ones(len(index), dtype=bool)
    used = valid & accepted_scope
    excluded_quality = recorded & ~(detected & respect_nonwear) & ~manual & ~valid
    values = series.to_numpy(dtype=float)

    def iterator():
        for i, timestamp in enumerate(index):
            reasons = []
            if not recorded[i]:
                reasons.append("recording_gap_or_missing")
            if detected[i] and respect_nonwear and recorded[i]:
                reasons.append("detected_nonwear")
            if manual[i] and recorded[i]:
                reasons.append("manual_mask")
            if excluded_quality[i]:
                reasons.append("invalid_quality_window")
            if mode == "selected" and not in_interval[i]:
                reasons.append("outside_selected_interval")
            yield [
                timestamp.isoformat(),
                float(values[i]) if recorded[i] else "",
                float(values[i]) if used[i] else "",
                units,
                int(recorded[i]),
                int(recorded[i] and detected[i]),
                int(recorded[i] and detected[i] and respect_nonwear),
                int(recorded[i] and manual[i]),
                int(excluded_quality[i]),
                int(in_interval[i]),
                int(used[i]),
                ";".join(reasons),
            ]

    return iterator(), len(index)


def write_processed_activity_archive(
    path, source_raw, analysis_raw, *, source_names, mapping_details,
    signal_settings, analysis_config, data_quality, support_summary,
    processing_provenance, participant_join=None, analysis_source_name=None,
    csv_mapping=None, csv_separator=",",
):
    """Write CSV and a machine-readable methods/provenance manifest to a ZIP."""
    window_settings = (analysis_config or {}).get("analysisWindowSettings", {}) or {}
    primary_label = (
        f"Joined participant ({' + '.join(source_names)})" if len(source_names) > 1
        else (source_names[0] if source_names else "Recording")
    )
    window_settings = {**window_settings, "sourceFileName": analysis_source_name or primary_label}
    units = (mapping_details or {}).get("units") or "unspecified"
    rows, epoch_count = processed_activity_rows(
        source_raw, analysis_raw, units=units,
        analysis_window_settings=window_settings, data_quality=data_quality,
    )
    software_versions = {}
    for name in ("pyActigraphy", "numpy", "pandas", "scipy", "pygt3x"):
        try:
            software_versions[name] = package_metadata.version(name)
        except package_metadata.PackageNotFoundError:
            software_versions[name] = None
    manifest = {
        "schema_version": "actilab-processed-activity-export-1.0",
        "exported_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_files": list(source_names),
        "epoch_count": epoch_count,
        "epoch_seconds": (data_quality or {}).get("epoch_seconds"),
        "unit": units,
        "activity_mapping": mapping_details,
        "csv_column_mapping": csv_mapping or {},
        "csv_separator": csv_separator,
        "software_versions": software_versions,
        "raw_signal_processing_settings": signal_settings,
        "analysis_config": analysis_config,
        "data_quality": data_quality,
        "support_file_summary": support_summary,
        "participant_join": participant_join,
        "processing_provenance": processing_provenance,
        "column_definitions": {
            "timestamp": "Timestamp from the recording, without inferred timezone conversion.",
            "processed_activity_pre_qc": "Epoch-level activity after raw filtering/magnitude/normalization and chosen activity metric, before masks and valid-day exclusion. Missing recordings are blank, never zero.",
            "activity_used_for_analysis": "Same epoch-level activity value, blank where excluded by QC or (in selected-only analysis) outside selected intervals. For 'both' analysis this column represents the whole-recording branch.",
            "unit": "Unit of the processed epoch-level activity metric; may be counts, derived values or acceleration units depending on mapping.",
            "recorded": "1 where an epoch contains finite processed activity data; 0 indicates missing data/gap.",
            "detected_nonwear": "1 where the reader/mapping supplies a non-wear mask (regardless of whether respecting it was enabled).",
            "nonwear_exclusion_applied": "1 where non-wear was excluded based on analysis QC settings.",
            "manually_masked": "1 where a user/uploaded mask interval excludes a recorded epoch.",
            "excluded_by_quality_window": "1 where a recorded epoch was otherwise eligible but belongs to a quality window failing the valid-hours threshold.",
            "within_selected_interval": "1 where the epoch is within one or more selected analysis intervals; always 1 in whole-file mode.",
            "included_in_final_analysis": "1 where the activity sample passed QC and, for interval-only mode, fell inside the selected interval(s).",
            "exclusion_reason": "Semicolon-delimited reasons. Values are blank when the epoch is included.",
        },
        "notes": [
            "This export contains the epoch-level activity signal provided to pyActigraphy, not the native high-frequency X/Y/Z samples or sleep-wake scoring predictions.",
            "Activity processing is performed again from the uploaded file(s), with the saved settings from the completed run. No further normalization or filtering is applied to the exported values.",
            "An interval-only run may calculate each interval separately and average metrics; activity_used_for_analysis contains their eligible epoch-level input, not the averaged metric results.",
            "A joined participant may have unrecorded intervals between files; these appear as blank activity values with recorded=0.",
            "Timestamps are represented as stored by the reader. Validate timezone and DST assumptions before merging data across devices.",
        ],
    }
    archive_path = Path(path)
    archive_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=5) as archive:
        with archive.open("preprocessed_activity.csv", "w") as stream:
            with io.TextIOWrapper(stream, encoding="utf-8", newline="") as text_stream:
                writer = csv.writer(text_stream)
                writer.writerow(COLUMNS)
                writer.writerows(rows)
        archive.writestr(
            "processing_manifest.json",
            json.dumps(make_json_safe(manifest), ensure_ascii=False, indent=2, allow_nan=False),
        )
        archive.writestr(
            "README.txt",
            "ActiLab processed epoch-level activity export\n\n"
            "preprocessed_activity.csv: one row per epoch, including missing/gap epochs, "
            "processed values before QC, the usable analysis value, and exclusion flags.\n"
            "processing_manifest.json: complete settings, input activity mapping, QC, "
            "analysis window configuration, provenance/methods and source list.\n\n"
            "For interval-only mode, the analysis value is blank outside selected intervals.\n"
            "For combined full-file + selected-interval analysis, the activity value "
            "represents the full-file branch; use within_selected_interval for the interval branch.\n"
            "Keep this archive with the final metric results for reproducibility.\n",
        )
    return {"epoch_count": epoch_count, "unit": units, "file_name": archive_path.name}
