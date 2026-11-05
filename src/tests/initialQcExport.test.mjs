import test from "node:test";
import assert from "node:assert/strict";
import { buildInitialQcRows, buildInitialQcCsv } from "../services/initialQcExport.js";

const windows = [
  { date: "2026-01-01", window_start: "2026-01-01T00:00:00", window_stop: "2026-01-02T00:00:00", window_label: "2026-01-01", expected_hours: 24, recorded_hours: 20, recording_gap_hours: 4, detected_nonwear_hours: 3, analyzable_hours: 17, manual_mask_hours: 0, valid_day: true },
  { date: "2026-01-02", window_start: "2026-01-02T00:00:00", window_stop: "2026-01-03T00:00:00", window_label: "2026-01-02", expected_hours: 24, recorded_hours: 10, recording_gap_hours: 14, detected_nonwear_hours: 0, analyzable_hours: 10, manual_mask_hours: 0, valid_day: false },
];
const entry = { key: "a", file: { name: "=EVAL(1).bin" } };
const qc = { a: { source_file_name: entry.file.name, inspection_stage: "initial_after_load_before_manual_preprocessing", detected_input_type: "geneactiv_bin_accelerometer", detected_nonwear_available: true, epoch_seconds: 30, recording_start: "2026-01-01", recording_end: "2026-01-02", participant_join: { source_files: [entry.file.name] }, modes: { calendar_day: { windows } } } };

test("initial QC exports all window rows and honors the current validity settings", () => {
  const result = buildInitialQcRows([entry], qc, { validDayWindowMode: "calendar_day", minimumValidHoursPerDay: 18, respectNonwear: true });
  assert.equal(result.length, 2);
  assert.equal(result[0].hours_used_for_validity, 17);
  assert.equal(result[0].valid_at_selected_settings, false);
  assert.equal(result[0].valid_at_initial_16h_rule, true);
  assert.equal(result[1].recording_gap_hours, 14);
  const withoutWear = buildInitialQcRows([entry], qc, { minimumValidHoursPerDay: 18, respectNonwear: false });
  assert.equal(withoutWear[0].hours_used_for_validity, 20);
  assert.equal(withoutWear[0].valid_at_selected_settings, true);
});

test("combined export excludes unfinished recordings and guards formula filenames", () => {
  const csv = buildInitialQcCsv([entry, { key: "not-ready", file: { name: "missing.bin" } }], qc, {});
  assert.match(csv, /'\=EVAL\(1\)\.bin/);
  assert.equal(csv.split("\n").filter(Boolean).length, 3);
  assert.ok(csv.startsWith("\uFEFFsource_file,"));
});

test("unknown nonwear is reported as unavailable, not confirmed zero", () => {
  const custom = structuredClone(qc);
  custom.a.detected_nonwear_available = false;
  const row = buildInitialQcRows([entry], custom, {})[0];
  assert.equal(row.detected_nonwear_available, false);
  assert.equal(row.detected_nonwear_hours, null);
});

test("joined mode only exports the joined timeline", () => {
  const joined = structuredClone(qc);
  joined.a.participant_join.source_files = ["part-1.bin", "part-2.bin"];
  assert.equal(buildInitialQcRows([entry], joined, {}).length, 2);
  assert.match(buildInitialQcCsv([entry], joined, {}), /part-1\.bin \| part-2\.bin/);
});
