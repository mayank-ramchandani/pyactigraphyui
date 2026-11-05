/** Step 2 descriptive QC CSV (no downstream analysis, masks or sleep scoring). */
import { rowsToCsv } from "./exportUtils.js";

export const INITIAL_QC_COLUMNS = [
  "source_file", "source_files_joined", "inspection_stage", "input_type",
  "quality_window_mode", "quality_window_label", "window_start", "window_stop", "date",
  "recording_start", "recording_end", "epoch_seconds", "timeline_hours",
  "total_recorded_hours", "total_recording_gap_hours", "detected_nonwear_available",
  "expected_hours", "recorded_hours", "recording_gap_hours", "detected_nonwear_hours",
  "manual_mask_hours", "analyzable_hours_before_manual_masks",
  "respect_detected_nonwear", "hours_used_for_validity", "minimum_valid_hours",
  "valid_at_selected_settings", "valid_at_initial_16h_rule", "exclusion_reason_initial_16h",
];

/** Return a row for each available QC window for a collection of uploaded files. */
export function buildInitialQcRows(entries, qcByFile, settings = {}) {
  const mode = settings.validDayWindowMode === "recording_anchored" ? "recording_anchored" : "calendar_day";
  const threshold = Number(settings.minimumValidHoursPerDay ?? 16);
  const minHours = Number.isFinite(threshold) && threshold >= 0 && threshold <= 24 ? threshold : 16;
  const respectNonwear = settings.respectNonwear !== false;
  return entries.flatMap((entry) => {
    const payload = qcByFile?.[entry.key];
    if (!payload || !payload.modes?.[mode]?.windows) return [];
    const joinedNames = payload.participant_join?.source_files || [entry.file?.name || "Unnamed file"];
    return payload.modes[mode].windows.map((window) => {
      const recorded = Number(window.recorded_hours) || 0;
      const analyzable = Number(window.analyzable_hours) || 0;
      const used = respectNonwear ? analyzable : recorded;
      return {
        source_file: payload.source_file_name || entry.file?.name || "Unnamed file",
        source_files_joined: joinedNames.join(" | "),
        inspection_stage: payload.inspection_stage,
        input_type: payload.detected_input_type,
        quality_window_mode: mode,
        quality_window_label: window.window_label,
        window_start: window.window_start,
        window_stop: window.window_stop,
        date: window.date,
        recording_start: payload.recording_start,
        recording_end: payload.recording_end,
        epoch_seconds: payload.epoch_seconds,
        timeline_hours: payload.timeline_hours,
        total_recorded_hours: payload.recorded_hours,
        total_recording_gap_hours: payload.recording_gap_hours,
        detected_nonwear_available: Boolean(payload.detected_nonwear_available),
        expected_hours: window.expected_hours,
        recorded_hours: window.recorded_hours,
        recording_gap_hours: window.recording_gap_hours,
        detected_nonwear_hours: payload.detected_nonwear_available ? window.detected_nonwear_hours : null,
        manual_mask_hours: window.manual_mask_hours,
        analyzable_hours_before_manual_masks: window.analyzable_hours,
        respect_detected_nonwear: respectNonwear,
        hours_used_for_validity: used,
        minimum_valid_hours: minHours,
        valid_at_selected_settings: used + 1e-9 >= minHours,
        valid_at_initial_16h_rule: window.valid_day,
        exclusion_reason_initial_16h: window.exclusion_reason,
      };
    });
  });
}

export function buildInitialQcCsv(entries, qcByFile, settings) {
  const rows = buildInitialQcRows(entries, qcByFile, settings);
  // Filenames and labels may be attacker-controlled; prevent spreadsheet formula injection.
  const safe = rows.map((row) => Object.fromEntries(Object.entries(row).map(([key, value]) => [
    key, typeof value === "string" && /^[\s]*[=+@-]/.test(value) ? `'${value}` : value,
  ])));
  return rows.length ? `\uFEFF${rowsToCsv(safe, INITIAL_QC_COLUMNS)}\n` : "";
}
