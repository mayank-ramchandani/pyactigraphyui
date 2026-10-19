# ActiLab plug-and-play workflow: implemented capabilities and scientific limits

**Updated 19 October 2026.** Applies to this source revision, not an independently validated GGIR replacement. *Recommended* means a practical ActiLab default, not a universally validated sleep or activity pipeline.

## 1. Format identification and available input signals

The loader inspects the filename **and** recognizable file contents to choose a reader. GENEActiv `.bin` contents are identified rather than assuming every BIN file is GENEActiv. `.gt3x` uses the GT3X reader. `.cwa` requires the Oxford/accelerometer-compatible conversion path; this does not expose the same streaming custom-filter controls as native BIN/GT3X. CSV and Excel readers detect timestamp, count/activity, light, temperature, non-wear, and (when present) X/Y/Z column names. Manual CSV mapping overrides these suggestions.

| Input | Presently supported processing | Important limitation |
|---|---|---|
| GENEActiv BIN | Streaming raw XYZ to activity representation, epoch reduction, light when present; configurable raw filter when enabled | No claim of identical GGIR calibration/non-wear/sleep processing |
| GT3X with raw XYZ | Streaming raw XYZ to activity, optional light; configurable raw filtering | Some files carry only counts or have incompatible streams; check diagnostics |
| CWA | Oxford conversion to an epoch-level activity representation | Server capacity and conversion dependencies limit files; custom raw-axis filters are unavailable |
| ActiGraph AGD / Actiwatch AWD / other native counts | Preserve counts and source-defined sampling period | Cannot reconstruct raw acceleration or recalculate ENMO from counts |
| Generic CSV with timestamp and activity | Use supplied activity and its native epoch; mapping is automatic when unambiguous | Count/activity units and algorithm validity are the analyst's responsibility |
| Generic CSV with X, Y, Z | Explicit units (g, mg, m/s²); calculate ENMO, MAD, PIM, ZCM or TAT within selected epoch | Does **not** run GGIR auto-calibration, static-angle sleep pipeline, or customizable raw-axis filtering; custom XYZ with ambiguous units must be mapped manually |
| Oxford timeSeries CSV | Existing accelerated/precomputed activity metrics | Existing epochs are not resampled into new raw features |

**Recognized XYZ headers:** `x_g`/`y_g`/`z_g`, corresponding `_mg` or `_ms2` names, `acc_x`/`acc_y`/`acc_z`, `accel_x`/`accel_y`/`accel_z`, or plain `x`/`y`/`z`. Automatic unit inference occurs **only** when all three column names explicitly declare one matching unit. For plain XYZ, select the unit in Step 1's *Manual CSV Column Mapping*. A missing unit is an error rather than an assumed g value. Axes are not treated as pre-computed activity counts.

CSV XYZ analysis groups raw readings into the selected epoch, and uses the time interval between samples to calculate PIM and TAT. This assumes approximately regular sampling; analyze severe gaps or irregular sampling with caution. ZCM requires a fixed milligravity threshold for CSV XYZ. Native GT3X/BIN may also use an adaptive threshold according to their existing streaming pipeline.

## 2. Recommended preprocessing and activity epochs

ActiLab's **existing** auto source mapping uses vendor activity for count files and processed `acc` for supported accelerometer inputs. If your research protocol specifically requires GGIR-style acceleration magnitudes, choose **ENMO** explicitly in Step 3. The ENMO calculation is the epoch mean of `max(sqrt(x²+y²+z²) - 1 g, 0)` in mg. MAD is mean absolute deviation of norm within each epoch. These are not equivalent to activity counts.

| Config | Resolved initial setting | Notes |
|---|---|---|
| Activity representation | Auto (source activity or existing processed acc) | Visible in results and metadata; **not** automatically the same as GGIR ENMO |
| Raw activity epoch | **30 s** (ActiLab legacy default) | Select 5, 10, 15, 30 or 60 s in Step 3 before preview/analysis. 5 s is the GGIR short-epoch reference. A native counts/epoch file retains its input epoch. |
| Optional custom raw preprocessing | **Off** | Only native GT3X and verified GENEActiv BIN allow optional filters/magnitude/gravity settings. These settings carry over to downstream activity analysis and are recorded. |
| Missing data | Retain `NaN` / unavailable | Never convert gaps to zero movement. |
| Detected/mapped non-wear | Respect when provided | Does not claim GGIR detector equivalence across devices. |
| Minimum analyzable hours | **16 h/day** | ActiLab default, configurable in Step 7; do not misattribute this as the universal GGIR default. |
| Minimum consecutive quality windows for rhythm | **2** | Configurable in Step 7. |
| Sleep-window epoch coverage | **80%** | Configurable; exclude insufficient sleep windows. |
| Quality day | Calendar day | Optional recording-anchored 24h window. |

**Important:** Epoch length is a preprocessing choice. Values calculated with different epochs may not be directly comparable (especially PIM, ZCM, TAT and sleep scoring). Switching epoch length after Initial QC means you should recheck previews and masks and re-run the analysis. Converted CWA files may require Java/accelerometer processing and are subject to server limits.

## 3. Sleep and rest detection: implemented versus future work

The existing ActiLab sleep module offers the pyActigraphy algorithms surfaced in the Sleep-wake step (Cole–Kripke, Sadeh, Oakley, Crespo, Roenneberg and supported additional options). Where configured, Crespo_AoT and Roenneberg_AoT can infer main rest windows without a diary. A sleep diary/custom sleep window should be used when appropriate. Sleep windows that cannot be found or have insufficient valid coverage are **not fabricated**.

**GGIR's HDCZA sleep-period guider plus van Hees sustained inactivity bouts (SIB) has NOT been implemented in this revision**. The existing algorithms must not be described as a GGIR plug-and-play HDCZA equivalent. Particularly, classic count-based sleep scoring should not be assumed valid for arbitrary ENMO/mg acceleration and epoch durations. Tooltips in Step 6 display this caution for raw or count-based data, and the final QC payload warns when a classic count method is applied to raw acceleration. Device placement, population, input units, diary availability, validation literature and method-specific thresholds must be considered before choosing a scorer.

For GGIR-style sleep parity, future implementation must add verified angle-series handling, HDCZA guider, sustained inactivity bout detection, and matching missingness/non-wear/diary logic, and **then** benchmark against GGIR. The report should include the exact version of both pipelines, differences and limitations. Do not label comparisons as validated until tests have actually passed.

## 4. Exports — exact meaning of the two CSV files

Step 10 offers checkboxes for `actilab_daily.csv` and `actilab_aggregated.csv`, an always available `actilab_meta.json`, full results JSON, long-form metric CSV and the existing separately generated processed-activity ZIP. The same results for multiple analyzed files are concatenated into a common table, with `source_file` identifying each successful recording/participant; failed recordings appear in warnings but not in the numeric rows.

- **Daily CSV:** one row for each **QC quality window**, with date/start/stop, validity, recording gaps, non-wear, masked/analyzable hours, and mean/median activity computed from the **actual final valid-epoch mask**. When a selected existing sleep scorer actually produces eligible sleep windows, the daily CSV also includes real night TST, WASO, and sleep-efficiency values grouped by the **start date of the sleep window** (which may cross midnight). These are not synthesized GGIR HDCZA/SIB night values. Unscorable nights stay blank. Some windows have no valid acceleration value: the cells remain empty. In recording-anchored mode, the `date` is only an anchor; use the `window_start` and `window_stop` columns.
- **Aggregated CSV:** one row per analyzed recording (or joined participant) with valid window count, whole valid-epoch mean/median and **existing scalar recording-level analysis results** such as RA, IS, IV and sleep quantities where computed. A multi-day metric is not calculated by averaging the daily window rows. The selected-interval mode may return averaged interval metrics at the top result level; see `analysis_window_mode`, `analysis_windows` and full JSON.
- **Metadata JSON:** effective resolved signal processing, raw defaults, quality defaults, algorithm and metric parameters, configured windows and masks, original source mapping, requested/resolved activity basis, device reader, epoch duration, final QC summary, processing warnings and installed Python package versions, **including defaults not overridden by the user**. Per-file methods are stored under `recording_methods`. Also includes light results and diagnostics where present.

A bundled results export is a reproducible **research summary**, not a claim that its column names exactly match `GGIR` Part 2/4/5/6. The GGIR outputs include additional night-level and non-wear/calibration measures not all currently available from ActiLab. The candidate catalogue `METRIC_CATALOG_CANDIDATES.csv` distinguishes proposed/core/extended output metrics from implemented output columns and is **not** an implementation claim.

## 5. Verification against GGIR

See [GGIR comparison protocol](GGIR_COMPARISON_PROTOCOL.md), including matched-parameter constraints, a practical CLI comparator and requirements for verifying raw calibration, ENMO, wear, thresholds, sleep guidence and multi-day rhythm values. A name match is insufficient: align units, epoch, timezone, valid-day rules and algorithm definitions first.

## Scientific references

- GGIR accelerometry metric pipeline and 5-second default: https://wadpac.github.io/GGIR/articles/chapter4_AccMetrics.html
- GGIR algorithm, calibration and sleep parameters: https://wadpac.github.io/GGIR/articles/GGIRParameters.html
- pyActigraphy methods and parameters: https://ghammad.github.io/pyActigraphy/MetricsMixin.html
- pyActigraphy code and algorithms: https://github.com/ghammad/pyActigraphy
- Maczák B, et al. PLOS ONE 2021: https://doi.org/10.1371/journal.pone.0261718

Document any protocol deviations. These references define the scientific context but **do not** imply ActiLab is a validated replication of GGIR.
