# Where ActiLab's automatic processing comes from — by file type

**Applies to the code supplied 5 November 2026.** This is a description of *what the installed code actually does*, not a claim of GGIR compatibility or device-specific validation. In the user interface, “Auto / Recommended source” means *select a sensible available activity channel for the file* — **not** “run the full GGIR pipeline automatically.”

## Where the software and method definitions come from

ActiLab does **not** download algorithms dynamically from GGIR or other services. The backend imports installed Python packages or uses its own local readers. The shipped `backend/requirements.txt` pins `pyActigraphy==1.2.2`, `accelerometer==6.2.3` (Oxford `accProcess`), `pygt3x==0.7.1` and `agcounts==0.2.6`. Exact runtime versions must be verified from exported metadata because deployments can differ.

| What happens | Source used by ActiLab | Code location |
|---|---|---|
| Recognize native file / inspect CSV headers | ActiLab file heuristics and GENEActiv header checks | `backend/io_helpers.py`: `infer_reader_type`; `backend/accelerometer_loader.py` |
| Native counts/activity readers | **pyActigraphy** `pyActigraphy.io.read_raw_*` | `backend/io_helpers.py`: `READERS`, `load_native_file` |
| GENEActiv `.bin` streaming | **ActiLab's own** page/hex decoder, using GENEActiv metadata and per-axis calibration values stored in the recording | `backend/geneactiv_bin.py`: `read_raw_geneactiv_bin` |
| ActiGraph `.gt3x` streaming | `pygt3x` parser and optional GT3X-file CalibrationV2; ActiLab reduction, optional `agcounts`-style counts path | `backend/gt3x_loader.py` |
| Axivity `.cwa` / non-GENEActiv `.bin` conversion | **Oxford accelerometer** CLI `accProcess` (requires Java), then ActiLab imports generated `*timeSeries.csv(.gz)` | `backend/accelerometer_loader.py` |
| Generic CSV/TXT/Excel/ODS | ActiLab column detection, pandas, explicit mapping override | `backend/io_helpers.py`, `backend/app.py` |
| CSV raw X/Y/Z | ActiLab pandas resampling, units conversion and short-epoch metric definitions | `backend/tabular_xyz.py` |
| Optional raw-axis signal filtering | ActiLab streaming, causal SciPy Butterworth filtering (not GGIR) | `backend/raw_signal_processing.py` |
| Early QC and final QC | **ActiLab-specific** timestamp coverage / masks / ≥16-hour rule | `backend/data_quality.py` |
| Nonparametric metrics and sleep classifiers | Mainly **pyActigraphy** methods invoked by ActiLab, plus ActiLab aggregation and availability safeguards | `backend/analysis.py` |
| Daily/aggregated results and provenance | ActiLab (not GGIR output tables) | `backend/release_exports.py` |

**GGIR is a separate R package, not an ActiLab runtime dependency.** Its calibration, non-wear, ENMO reduction, HDCZA sleep guider and sustained inactivity bout routines do not automatically become part of ActiLab when an input is set to Auto. [GGIR official pipeline](https://wadpac.github.io/GGIR/articles/chapter2_Pipeline.html).

## Shared pipeline for every file

1. **Step 1 — Import**: identify the format from extension and, where appropriate, contents; load an existing timestamped activity series or convert raw X/Y/Z samples to a *single* selected metric at the specified epoch. `Auto` resolves by input type. CSV mapping can be confirmed or overridden. Combined recordings are first processed individually at native sampling rates and then joined into a common epoch timeline.
2. **Step 2 — Initial QC**: `inspect_initial_data_coverage` regularizes the epoch timestamps and reports one row per calendar day or recording-aligned 24-hour window. It counts finite, recorded activity values; absent timestamps and non-finite activity as gaps; and reader/mapped non-wear **only if a mask exists**. By default the display assesses ≥16 h. Manual exclusions, start/stop files and later analysis settings are **not yet applied**. The **Export initial QC CSV** control exports these existing results without running Step 9 or Step 10.
3. **Step 3 — Activity basis**: auto/source counts, processed `acc`, ENMO, MAD, PIM, ZCM or TAT are **alternatives**, not the same measure. Raw-supported files can change analytical epochs to 5, 10, 15, 30 or 60 seconds (default **30 s**); already epoch-aggregated counts/processed records cannot reconstruct raw values by merely changing the epoch control.
4. **Steps 4–6 — Preview, cleaning, sleep**: view the extracted series; optionally add start/stop boundaries, diaries, and manually masked/non-wear intervals. Select a specific sleep classifier. ActiLab does **not** auto-select a scientifically validated sleep algorithm by device, and its Cole–Kripke/Sadeh/Crespo/Roenneberg choices are **not equivalent** to GGIR HDCZA + SIB. Availability depends on the file and selected settings.
5. **Step 7 — Analysis settings**: defaults are calendar days, ≥16 valid hours, 2 consecutive valid windows for eligible multi-window measures, ≥80% valid sleep-window coverage, reader/mapped non-wear respected when present. These are **ActiLab defaults, not GGIR's defaults**.
6. **Steps 8–10 — Sensors, results and export**: apply final start/stop and masks; recalculate the **final** quality window table and valid epoch mask (`apply_data_quality_control`); analyze selected metrics; export final daily and aggregated CSV and metadata JSON. Non-finite/missing periods do not silently become recorded zero activity. Download the metadata for the effective per-recording settings.

### Format-specific path — source, intermediate activity, limitations

| Uploaded recording | Identification → reader / transformation → auto activity basis | What is *not* performed automatically |
|---|---|---|
| **GENEActiv `.bin`** | Detect GENEActiv-format header → `geneactiv_bin.read_raw_geneactiv_bin` streams pages → header gain/offset calibration and X/Y/Z magnitude → default processed `acc` (20-Hz magnitude low-pass when feasible), epoch aggregation; optional direct ENMO/MAD/PIM/ZCM/TAT. Light and temperature extracted if available. | **No GGIR multi-day gravity auto-calibration** or GGIR-identical non-wear detection; the new native-X/Y/Z 60-minute GGIR-inspired screen is applied to initial QC, and automatic HDCZA/SIB is not available. Header calibration ≠ GGIR auto-calibration. Custom filtering is optional, off by default. |
| **ActiGraph `.gt3x`** | Identify GT3X → `pygt3x` streaming events → apply supported calibration information from GT3X, reduce X/Y/Z → default processed `acc` / optional ENMO/MAD/PIM/ZCM/TAT or original counts when supported. Uses `agcounts`-compatible conversion where applicable; light extracted only when present. | A GGIR-inspired native X/Y/Z non-wear screen is used for QC but is **not** GGIR-identical. No GGIR-calibration parity; counts and mg metrics have different units. Unsupported event types/calibration should be checked in diagnostics. |
| **Axivity `.cwa`** | Detect CWA → **Oxford `accProcess`** → `*timeSeries.csv(.gz)` → map its `acc` column to an epoch activity series (or select preexisting supported output column). | Not natively streamable for custom raw filtering in this build. Server-side conversion requires `accProcess`/Java and has an **environment-configurable size gate (default 2 MB)**; convert large recordings locally. AccProcess is **not GGIR**. |
| **Other `.bin`** (not GENEActiv) | Header recognition fails → attempt Oxford `accProcess` path → epoch-level output | File may be unsupported by Oxford; arbitrary binary files are not guaranteed compatible. |
| **Oxford `*timeSeries.csv` / `.csv.gz`** | Identify `time` + compatible `acc`, `ENMO`, `MAD`, etc. headers → Oxford CSV reader → **prefer existing `acc`** for Auto; map explicit `ENMO`, `MAD`, `PIM`, `ZCM` or `TAT` when columns are present. | No new raw calibration, axes filtering, or reconstruction of absent metrics; source `acc` is not necessarily the same as GGIR ENMO. |
| **ActiGraph `.agd`** | `.agd` → `pyActigraphy.io.read_raw_agd` → native device activity/counts and original epoch | Does not infer ENMO or MAD from counts. |
| **Actigraph `.atr`** | `.atr` or recognizable ATR delimited export → `pyActigraphy.io.read_raw_atr` → device's standard activity; optional reader-native `PIM`/`ZCM`/`TAT` modes | Reader-native count modes are not raw-XYZ reconstruction. |
| **Actiwatch `.awd`** | `.awd` → `pyActigraphy.io.read_raw_awd` → source activity | No raw X/Y/Z or GGIR calibration available from counts. |
| **Daqtix `.dqt`, BBA `.bba`, MESA `.mesa`, MTN `.mtn`, TAL `.tal`** | Recognize extension/header → matching `pyActigraphy.io.read_raw_dqt/bba/mesa/mtn/tal` → native activity series | Analysis depends on each reader's actual data coverage and channels. No raw accelerometry features reconstructed from a count series. |
| **Philips Actiware `.rpx` or localized Actiware CSV/TXT** | RPX / English-French-German header detection → localized CSV epoch parser when needed, otherwise pyActigraphy RPX reader → device count/activity series; RGB/white light if present | Not all localized exports have light; no accelerometer raw calibration. |
| **Generic CSV/TXT** | Timestamp/activity/light/temperature/non-wear headers detected → mapped pandas frame → `BaseRaw`; manual column mapping supported | The supplied activity column is taken **as supplied**; it is not assumed calibrated ENMO or mg. No raw filtering without true XYZ. |
| **Generic CSV with raw XYZ** | Detect X/Y/Z + timestamp, **require known g/mg/m·s⁻² units** → `tabular_xyz.load_xyz_as_baseraw` → resample to selected short epoch; Auto resolves to ENMO | No GGIR auto-calibration / raw-axis filtering; must inspect timestamp regularity. Over 5 million samples is blocked in this loader. |
| **Excel `.xls/.xlsx`, ODS `.ods`** | pandas spreadsheet reader → column detection/manual mapping → device/mapped activity or XYZ conversion | Raw high-frequency recordings are better handled in supported streaming formats; no vendor parser or device calibration inferred from the spreadsheet. |

**Automatic mapping clarification:** For **native BIN/GT3X**, `Auto` is currently the processed `acc` activity basis, not automatically ENMO. For **Oxford data**, Auto prefers `acc`, then source activity, then ENMO where present. For **native device count formats**, Auto uses the reader's source series. For **generic XYZ CSV**, Auto uses ENMO; it does not apply the optional raw-axes Butterworth module. Source provenance is recorded in the final export's per-file methods.

## Standard processing vs. optional advanced raw preprocessing

For native GENEActiv BIN and GT3X only, Step 2 can enable an **optional** streaming filter pipeline: calibrated raw X/Y/Z → Butterworth low-/high-/band-pass (on axes or magnitude, according to settings) → norm / gravity subtraction or alternate normalization → chosen epoch metric → final analysis. Filtering is **causal**, resets at sample discontinuities and is not the same zero-phase filtering/auto-calibration pipeline used by other packages. Default is **OFF**. See [Preprocessing and provenance](PREPROCESSING_AND_PROVENANCE.md).

For ZCM and TAT on native raw files, Auto threshold means a recording-specific adaptive SD-based threshold; a fixed mg threshold can instead be selected. For generic XYZ CSV, **fixed threshold is required**. The selected threshold and epoch affect reported units/values.

## What Step 2 quick QC does and does not tell you

- Initial QC measures **coverage of the activity epoch series after its initial reader/reduction**, not a cheap raw-file header-only scan. A 1 GB BIN still has to be decoded and reduced before its QC table can be produced. Full analysis is **not** necessary for the QC-only export.
- For a boundary calendar day, `recording_gap_hours` includes the hours outside that day's available recording coverage because each expected day is considered 24 hours. It is not strictly a measure of packet loss or non-wear inside recording time.
- If `detected_nonwear_available` is false, an exported non-wear cell is intentionally left blank: it does not prove that the participant wore the sensor for the entire period.
- `valid_at_initial_16h_rule` is the backend's initial flag, while `valid_at_selected_settings` follows the validity threshold and non-wear option currently shown in the UI. Re-run final analysis if manual masks/settings change.
- In joined mode the QC CSV contains the **joined participant timeline**, not separate QC for each constituent file. To obtain per-device QC, inspect in separate-file mode.
- Step 9 final QC includes masks and valid-window exclusions, and is the correct source for the final analytical sample. The Step 2 CSV must not be reported as if it were final QC.

## References and implementation provenance

- [pyActigraphy documentation and repository](https://github.com/ghammad/pyActigraphy)
- [Oxford accelerometer package](https://github.com/OxWearables/accelerometer)
- [GGIR documentation: Pipeline and Parts 1–6](https://wadpac.github.io/GGIR/articles/chapter2_Pipeline.html)
- [GGIR parameters and quality assessment](https://wadpac.github.io/GGIR/articles/GGIRParameters.html)
- [GGIR output schemas](https://wadpac.github.io/GGIR/articles/GGIRoutput.html)
- Maczák et al. 2021, [doi:10.1371/journal.pone.0261718](https://doi.org/10.1371/journal.pone.0261718)

For reproducibility, also archive the actual source file checksum, effective metadata JSON, selected mapping/epoch, runtime package versions, study timezone and any analysis configuration. The references document underlying concepts; they do **not** validate numerical equivalence between ActiLab and GGIR.
