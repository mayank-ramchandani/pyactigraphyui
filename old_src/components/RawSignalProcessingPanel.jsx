import React from "react";

const PAPER_URL = "https://doi.org/10.1371/journal.pone.0261718";

const PRESETS = {
  default: { enabled: false },
  magnitude: { enabled: true, filter_type: "none", filter_stage: "axes", normalization: "none", output_unit: "mg" },
  dynamic: { enabled: true, filter_type: "none", filter_stage: "axes", normalization: "positive_deviation", output_unit: "mg" },
  deviation: { enabled: true, filter_type: "none", filter_stage: "axes", normalization: "absolute_deviation", output_unit: "mg" },
  bandpass: { enabled: true, filter_type: "bandpass", filter_stage: "axes", filter_order: 3, low_cutoff_hz: 0.25, high_cutoff_hz: 2.5, normalization: "none", output_unit: "mg" },
};

export const DEFAULT_RAW_SIGNAL = {
  enabled: false,
  filter_type: "none",
  filter_stage: "axes",
  filter_order: 3,
  low_cutoff_hz: 0.25,
  high_cutoff_hz: 2.5,
  normalization: "positive_deviation",
  gravity_g: 1,
  output_unit: "mg",
};

export function InfoBubble({ text }) {
  return <span className="raw-signal-info" tabIndex={0} aria-label={text} role="note">
    <span aria-hidden="true">i</span><span className="raw-signal-info-popup">{text}</span>
  </span>;
}

function Field({ label, help, children }) {
  return <label className="raw-signal-field"><span className="raw-signal-label">{label} <InfoBubble text={help} /></span>{children}</label>;
}

const SELECT_STYLE = { width: "100%", minWidth: 0, padding: "9px 10px", borderRadius: 9, background: "white", color: "#0f172a", border: "1px solid #cbd5e1", boxSizing: "border-box" };

export default function RawSignalProcessingPanel({ settings = {}, onChange = () => {}, activityMapping = "auto" }) {
  const current = { ...DEFAULT_RAW_SIGNAL, ...settings };
  const patch = (values) => onChange({ ...current, ...values });
  const filtered = current.filter_type !== "none";
  const removesGravity = ["highpass", "bandpass"].includes(current.filter_type);
  const incompatibleGravity = removesGravity && ["subtract_one", "absolute_deviation", "positive_deviation"].includes(current.normalization);
  const incompatibleEnmo = activityMapping === "enmo" && current.normalization !== "positive_deviation";
  const incompatibleOriginal = activityMapping === "original";
  const needsLower = ["highpass", "bandpass"].includes(current.filter_type);
  const needsUpper = ["lowpass", "bandpass"].includes(current.filter_type);
  return (
    <section className="raw-signal-panel">
      <div className="raw-signal-heading"><div>
        <h3>Raw acceleration signal processing <InfoBubble text="Optional preprocessing on calibrated high-frequency X/Y/Z recordings, before epoch aggregation and before sleep/circadian analysis. These settings do not apply to count-based or already-aggregated data." /></h3>
        <p>Choose how raw acceleration becomes the signal used to calculate activity. When enabled, the transformed epoch-level activity is used in Initial QC, activity previews and plots, masking, rhythm metrics, and downstream activity/sleep analysis. Existing ActiLab processing is preserved unless custom processing is enabled. <InfoBubble text="The chosen raw settings are applied before aggregation to the Step 3 activity measure. Plots and rest/activity analyses use that epoch series rather than the unprocessed samples. Original X/Y/Z diagnostics and independently recorded light/temperature remain unchanged. Count-based sleep scoring is not validated automatically for modified acceleration inputs." /></p>
      </div></div>
      <label className="raw-signal-enable">
        <input type="checkbox" checked={Boolean(current.enabled)} onChange={(event) => patch({ enabled: event.target.checked })} />
        <span>Enable custom raw acceleration preprocessing</span>
        <InfoBubble text="Default (off) leaves each ActiLab activity metric's existing signal definition untouched. Enabling this changes the scientific input signal and may affect downstream results." />
      </label>
      {current.enabled && <>
        <div className="raw-signal-grid">
          <Field label="Starting configuration" help="Presets are optional starting points. You can change any compatible setting below.">
            <select style={SELECT_STYLE} value="" onChange={(e) => { if (PRESETS[e.target.value]) patch(PRESETS[e.target.value]); }}>
              <option value="">Custom (current settings)</option>
              <option value="magnitude">Unfiltered acceleration magnitude</option>
              <option value="dynamic">Positive magnitude minus gravity</option>
              <option value="deviation">Absolute magnitude deviation from gravity</option>
              <option value="bandpass">Illustrative 0.25–2.5 Hz band-pass (axes)</option>
              <option value="default">Restore existing ActiLab processing</option>
            </select>
          </Field>
          <Field label="Filter type" help="Butterworth low-pass retains frequencies below a cutoff; high-pass retains frequencies above it; band-pass retains a frequency range. 'No filter' retains calibrated samples.">
            <select style={SELECT_STYLE} value={current.filter_type} onChange={(e) => patch({ filter_type: e.target.value, ...(["highpass", "bandpass"].includes(e.target.value) && ["subtract_one", "absolute_deviation", "positive_deviation"].includes(current.normalization) ? { normalization: "none" } : {}) })}>
              <option value="none">No filtering</option><option value="lowpass">Low-pass</option><option value="highpass">High-pass</option><option value="bandpass">Band-pass</option>
            </select>
          </Field>
          <Field label="Filter order" help="Butterworth order controls roll-off steepness. Allowed orders 1–8. ActiLab uses causal forward-only filtering on streaming raw data.">
            <input type="number" min="1" max="8" step="1" disabled={!filtered} style={SELECT_STYLE} value={current.filter_order} onChange={(e) => patch({ filter_order: e.target.value })} />
          </Field>
          <Field label="Filter applied to" help="Filtering X, Y and Z separately before vector magnitude is different from filtering the scalar magnitude afterward. In the latter case, band/high-pass filtering can produce signed values.">
            <select style={SELECT_STYLE} disabled={!filtered} value={current.filter_stage} onChange={(e) => patch({ filter_stage: e.target.value })}>
              <option value="axes">Each axis first, then magnitude</option><option value="magnitude">Magnitude first, then filter</option>
            </select>
          </Field>
          {needsLower && <Field label="Lower / high-pass cutoff (Hz)" help="High-pass corner frequency, or the lower edge of a band-pass. Must be greater than 0 and below half the native sampling frequency.">
            <input type="number" min="0.001" step="any" style={SELECT_STYLE} value={current.low_cutoff_hz} onChange={(e) => patch({ low_cutoff_hz: e.target.value })} />
          </Field>}
          {needsUpper && <Field label="Upper / low-pass cutoff (Hz)" help="Low-pass corner frequency, or the upper edge of a band-pass. Must be less than half the recorded samples per second (Nyquist frequency).">
            <input type="number" min="0.001" step="any" style={SELECT_STYLE} value={current.high_cutoff_hz} onChange={(e) => patch({ high_cutoff_hz: e.target.value })} />
          </Field>}
          <Field label="Gravity normalization" help="Magnitude = √(X²+Y²+Z²). 'Subtract gravity' is signed (magnitude − reference g); 'absolute deviation' is |magnitude − reference g|; 'positive deviation' is max(magnitude − reference g, 0). Absolute amplitude takes |signal| without removing gravity.">
            <select style={SELECT_STYLE} value={current.normalization} onChange={(e) => patch({ normalization: e.target.value })}>
              <option value="none">None (keep signed/magnitude values)</option><option value="absolute">Absolute amplitude (no gravity subtraction)</option>
              <option value="subtract_one">Subtract gravity reference (signed)</option><option value="absolute_deviation">Absolute deviation from gravity</option>
              <option value="positive_deviation">Positive deviation from gravity (ENMO)</option>
            </select>
          </Field>
          <Field label="Gravity reference (g)" help="Usually 1 g for calibrated acceleration. This value is subtracted only by gravity-deviation normalization modes. It is NOT a replacement for sensor calibration.">
            <input type="number" min="0.1" max="2" step="0.001" disabled={["none", "absolute"].includes(current.normalization)} value={current.gravity_g} style={SELECT_STYLE} onChange={(e) => patch({ gravity_g: e.target.value })} />
          </Field>
          <Field label="Output acceleration unit" help="The raw loaders work internally in units of g and mg. This changes the final epoch values after aggregation; ZCM crossing counts and TAT durations do not depend on the displayed acceleration unit. Thresholds for ZCM/TAT remain in mg.">
            <select value={current.output_unit} style={SELECT_STYLE} onChange={(e) => patch({ output_unit: e.target.value })}>
              <option value="mg">mg (milligravity)</option><option value="g">g (gravity)</option><option value="m_s2">m/s² (SI acceleration)</option>
            </select>
          </Field>
        </div>
        {incompatibleGravity && <p className="raw-signal-warning">High-pass and band-pass filters attenuate the static gravity component; subtracting 1 g afterward is not valid here. Choose no gravity subtraction or absolute amplitude.</p>}
        {incompatibleEnmo && <p className="raw-signal-warning">The ENMO activity metric requires positive deviation from gravity. Select that option or change the activity metric to processed acceleration.</p>}
        {incompatibleOriginal && <p className="raw-signal-warning">Custom raw processing cannot be combined with device counts/source activity. Change the Step 3 activity metric to a raw-derived metric.</p>}
        <p className="raw-signal-footnote">Filtering uses a forward-only, stateful Butterworth filter that resets at recording gaps; it does not interpolate missing time. Filter parameters are validated against each file’s native sampling rate. Filtering, especially after magnitude calculation, may change signal sign and downstream metric interpretations. This is an exploratory processing option, not a validation of sleep-algorithm inputs. See <a href={PAPER_URL} target="_blank" rel="noreferrer">Maczák et al. (2021)</a>.</p>
      </>}
      {!current.enabled && <p className="raw-signal-footnote">Optional advanced controls are off. Choose a metric in Step 3 to use its established processing path. Custom filtering requires native raw X/Y/Z files (currently supported: GT3X and GENEActiv BIN).</p>}
    </section>
  );
}
