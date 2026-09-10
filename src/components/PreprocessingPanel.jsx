import React, { useMemo } from "react";
import { buildFileEntries, fileEntryLabel, formatFileSize } from "../services/fileIdentityUtils";
import SamplingHarmonizationNotice from "./SamplingHarmonizationNotice";

function formatHours(value) {
  const number = Number(value);
  if (!Number.isFinite(number)) return "—";
  return `${Number(number.toFixed(2))} h`;
}

function InitialQcCard({ entry, payload, loading, error, settings }) {
  const mode = settings.validDayWindowMode || "calendar_day";
  const modePayload = payload?.modes?.[mode] || {};
  const windows = modePayload.windows || [];
  const threshold = Number(settings.minimumValidHoursPerDay ?? 16);
  const respectNonwear = Boolean(settings.respectNonwear);
  const effectiveHours = (row) => Number(respectNonwear ? row.analyzable_hours : row.recorded_hours) || 0;
  const validCount = windows.filter((row) => effectiveHours(row) + 1e-9 >= threshold).length;
  const invalidCount = Math.max(0, windows.length - validCount);
  const modeLabel = mode === "recording_anchored" ? "recording-aligned 24-hour windows" : "calendar days";

  return (
    <details style={{ border: "1px solid #e2e8f0", borderRadius: 14, background: "white", overflow: "hidden" }}>
      <summary style={{ cursor: "pointer", padding: 13, listStyle: "none" }}>
        <div style={{ display: "grid", gridTemplateColumns: "minmax(0, 1fr) auto", gap: 12, alignItems: "center" }}>
          <div style={{ minWidth: 0 }}>
            <div style={{ fontWeight: 800, overflowWrap: "anywhere" }}>{fileEntryLabel(entry)}</div>
            <div style={{ color: "#64748b", fontSize: 12, marginTop: 3 }}>{formatFileSize(entry.file?.size)}</div>
          </div>
          <div style={{ textAlign: "right", fontSize: 13 }}>
            {loading ? (
              <span style={{ color: "#475569", fontWeight: 700 }}>Inspecting…</span>
            ) : error ? (
              <span style={{ color: "#991b1b", fontWeight: 800 }}>QC unavailable</span>
            ) : payload ? (
              <>
                <span style={{ color: validCount > 0 ? "#166534" : "#991b1b", fontWeight: 800 }}>{validCount} valid</span>
                <span style={{ color: "#64748b" }}> · {invalidCount} below threshold</span>
              </>
            ) : (
              <span style={{ color: "#64748b" }}>Queued</span>
            )}
          </div>
        </div>
      </summary>

      <div style={{ borderTop: "1px solid #e2e8f0", padding: 13 }}>
        {error && (
          <div style={{ border: "1px solid #fecaca", background: "#fef2f2", color: "#991b1b", borderRadius: 10, padding: 10, fontSize: 13 }}>
            {error}
          </div>
        )}
        {!error && loading && <div style={{ color: "#475569", fontSize: 13 }}>Loading the file and calculating initial per-day coverage. Large raw recordings may take longer to inspect.</div>}
        {!error && payload && (
          <>
            <SamplingHarmonizationNotice harmonization={payload?.participant_join?.sampling_harmonization} compact />
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(150px, 1fr))", gap: 10, marginBottom: 12 }}>
              <div style={{ background: "#f8fafc", borderRadius: 10, padding: 10 }}><strong>Recorded</strong><br />{formatHours(payload.recorded_hours)}</div>
              <div style={{ background: "#f8fafc", borderRadius: 10, padding: 10 }}><strong>Initial gaps</strong><br />{formatHours(payload.recording_gap_hours)}</div>
              <div style={{ background: "#f8fafc", borderRadius: 10, padding: 10 }}><strong>Window basis</strong><br />{modeLabel}</div>
              <div style={{ background: "#f8fafc", borderRadius: 10, padding: 10 }}><strong>Threshold applied here</strong><br />{threshold} h</div>
            </div>
            <div style={{ overflowX: "auto" }}>
              <table style={{ width: "100%", borderCollapse: "collapse", minWidth: 720, fontSize: 13 }}>
                <thead>
                  <tr>
                    <th style={{ textAlign: "left", padding: 7, borderBottom: "1px solid #e2e8f0" }}>Quality window</th>
                    <th style={{ textAlign: "right", padding: 7, borderBottom: "1px solid #e2e8f0" }}>Recorded</th>
                    <th style={{ textAlign: "right", padding: 7, borderBottom: "1px solid #e2e8f0" }}>Gap</th>
                    <th style={{ textAlign: "right", padding: 7, borderBottom: "1px solid #e2e8f0" }}>Detected non-wear</th>
                    <th style={{ textAlign: "right", padding: 7, borderBottom: "1px solid #e2e8f0" }}>Used for validity</th>
                    <th style={{ textAlign: "right", padding: 7, borderBottom: "1px solid #e2e8f0" }}>Valid</th>
                  </tr>
                </thead>
                <tbody>
                  {windows.map((row, index) => {
                    const hours = effectiveHours(row);
                    const valid = hours + 1e-9 >= threshold;
                    return (
                      <tr key={`${row.window_start || row.date}-${index}`}>
                        <td style={{ padding: 7, borderTop: "1px solid #e2e8f0", overflowWrap: "anywhere" }}>{row.window_label || row.date}</td>
                        <td style={{ padding: 7, borderTop: "1px solid #e2e8f0", textAlign: "right" }}>{formatHours(row.recorded_hours)}</td>
                        <td style={{ padding: 7, borderTop: "1px solid #e2e8f0", textAlign: "right" }}>{formatHours(row.recording_gap_hours)}</td>
                        <td style={{ padding: 7, borderTop: "1px solid #e2e8f0", textAlign: "right" }}>{formatHours(row.detected_nonwear_hours)}</td>
                        <td style={{ padding: 7, borderTop: "1px solid #e2e8f0", textAlign: "right" }}>{formatHours(hours)}</td>
                        <td style={{ padding: 7, borderTop: "1px solid #e2e8f0", textAlign: "right", color: valid ? "#166534" : "#991b1b", fontWeight: 800 }}>{valid ? "Yes" : "No"}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
            <div style={{ color: "#64748b", fontSize: 12, lineHeight: 1.5, marginTop: 10 }}>
              Initial QC is descriptive and occurs before start/stop restrictions and uploaded/manual masks. Final QC is recalculated during analysis.
            </div>
          </>
        )}
      </div>
    </details>
  );
}

export default function PreprocessingPanel({
  title = "2. Pre-processing",
  settings = {},
  actigraphyFiles = [],
  initialQcByFile = {},
  initialQcLoadingByFile = {},
  initialQcErrorByFile = {},
  participantFileMode = "separate",
  joinedParticipantKey = "__joined_participant__",
  joinedParticipantLabel = "Joined participant",
}) {
  const resolved = {
    customizeDataQualityThresholds: false,
    validDayWindowMode: "calendar_day",
    minimumValidHoursPerDay: 16,
    minimumValidDaysForRhythm: 2,
    minimumSleepWindowCoverage: 0.8,
    respectNonwear: true,
    ...settings,
  };
  const entries = useMemo(() => {
    if (participantFileMode === "join" && actigraphyFiles.length > 1) {
      const totalSize = actigraphyFiles.reduce((sum, file) => sum + (Number(file?.size) || 0), 0);
      return [{
        key: joinedParticipantKey,
        file: { name: joinedParticipantLabel || `Joined participant (${actigraphyFiles.length} files)`, size: totalSize },
        duplicateCount: 1,
        duplicateIndex: 1,
      }];
    }
    return buildFileEntries(actigraphyFiles);
  }, [actigraphyFiles, participantFileMode, joinedParticipantKey, joinedParticipantLabel]);

  return (
    <div style={{ background: "white", border: "1px solid #e2e8f0", borderRadius: 20, padding: 20 }}>
      <h2 style={{ marginTop: 0, marginBottom: 8 }}>{title}</h2>
      <p style={{ color: "#64748b", marginTop: 0, marginBottom: 18, lineHeight: 1.55 }}>
        Review initial data coverage before continuing through the workflow. Final analysis settings are configured in Step 8, Analysis Set-up.
      </p>

      <div style={{ border: "1px solid #bfdbfe", borderRadius: 16, padding: 16, background: "#eff6ff", marginBottom: 16 }}>
        <div style={{ fontWeight: 800, color: "#1e3a8a", marginBottom: 8 }}>Initial data-coverage QC after file loading</div>
        <div style={{ color: "#475569", fontSize: 13, lineHeight: 1.55, marginBottom: 12 }}>
          {participantFileMode === "join" && actigraphyFiles.length > 1
            ? "The joined participant timeline is inspected as one longitudinal recording, with real timestamp gaps retained as missing data. Expand it for the full table."
            : "Each uploaded recording is inspected before final preprocessing so you can see how much data is present in each candidate quality window. Expand a file for the full table."}
        </div>
        <div style={{ display: "grid", gap: 10 }}>
          {entries.map((entry) => (
            <InitialQcCard
              key={entry.key}
              entry={entry}
              payload={initialQcByFile[entry.key]}
              loading={Boolean(initialQcLoadingByFile[entry.key])}
              error={initialQcErrorByFile[entry.key]}
              settings={resolved}
            />
          ))}
          {entries.length === 0 && <div style={{ color: "#64748b" }}>Upload an actigraphy file in Step 1 to run initial QC.</div>}
        </div>
      </div>

    </div>
  );
}
