# Metrics and algorithms

The current workflow separates sleep-wake classification from metric selection:

- **page 6** selects sleep diaries/custom windows, automatic window estimation, and the sleep/rest algorithm;
- **page 8** selects analysis families or individual metrics and their parameters;
- **page 9** runs the analysis and displays results.

The machine-readable registries are:

- `config/metricRegistry.json`
- `config/algorithmRegistry.json`
- `config/analysisFamilyRegistry.json`
- `config/sharedParamRegistry.json`

## Rest-activity metrics

| Metric | Meaning |
|---|---|
| RA | Relative amplitude derived from M10 and L5 of the cyclic average daily profile. |
| IS | Interdaily stability, describing consistency of the 24-hour pattern across days. |
| IV | Intradaily variability, describing fragmentation or transitions within the day. |
| ISm / IVm | Mean forms returned by the corresponding pyActigraphy methods. |
| ISp / IVp / RAp | Period-specific outputs that may be vectors rather than scalars. |

### Relative amplitude

```text
RA = (M10 - L5) / (M10 + L5)
```

RA can equal 1 when L5 is zero and M10 is positive. Review M10/L5 values and start times, activity mapping, units, binarization, thresholds, gaps, non-wear, and masks before interpretation.

## Fragmentation metrics

| Metric | Meaning |
|---|---|
| kRA | Transition probability from rest to activity under the selected threshold/scoring setup. |
| kAR | Transition probability from activity to rest under the selected threshold/scoring setup. |

Availability depends on the raw-object interface and selected activity scale.

## Sleep metrics

| Metric | Meaning |
|---|---|
| SRI | Sleep Regularity Index over valid scored epoch pairs exactly 24 hours apart. |
| TST | Observed sleep time within an eligible selected window. |
| WASO | Observed wake after observed sleep onset within an eligible window. |
| Sleep efficiency | Sleep minutes divided by observed/scored window minutes. |

The pyActigraphy SRI definition ranges from -100 to 100; 100 means every available 24-hour pair has the same sleep/wake state. SRI is unavailable below the configured consecutive-valid-day requirement and may remain unavailable when no valid 24-hour pairs remain.

## Sleep/rest algorithms

The algorithm registry currently exposes Cole-Kripke, Sadeh, Oakley, Scripps, Crespo, and Roenneberg entries. Classic scoring algorithms were developed for specific devices, count scales, epochs, placements, and populations. Execution on a generic mg series does not establish validation for that combination.

## Diary/custom and automatic sleep windows

Page 6 accepts uploaded diaries and per-file custom plot-selected windows. When no diary window is available, `Crespo_AoT` or `Roenneberg_AoT` may estimate onset/offset windows through the Raw-like adapter.

The application:

- validates onset/offset pairs;
- filters by configured minimum and maximum duration;
- records method and parameters;
- applies the page-2 sleep-window coverage threshold;
- does not insert a fallback window.

A recording may return no usable window because of insufficient day/night contrast, gaps, non-wear, short duration, constant activity, unsuitable scale or threshold, resampling choices, or detector parameters. Roenneberg should generally be evaluated with 10-minute resampling as an initial configuration.

## Sleep-window coverage

At the default coverage threshold of 0.80:

- at least 80% of expected epochs in each sleep window must remain recorded and scorable;
- missing epochs are ignored rather than scored as wake;
- TST is observed sleep time and is not inflated to compensate for gaps;
- WASO counts observed wake after observed sleep onset;
- sleep efficiency uses observed/scored minutes as the denominator;
- scheduled window duration is returned separately;
- excluded windows retain an explicit QC reason.

## Analysis Set-up

Page 8 supports standard/default selection or custom family-level/metric-level selection. Shared parameters and metric-specific overrides are resolved into the analysis payload. Page 8 does not generate results.

## Reporting requirements

Every result should include:

- file ID and source filename;
- device/file format;
- requested and resolved activity mapping;
- units and epoch duration;
- preprocessing thresholds and intervals;
- sleep-window source;
- algorithm and parameters;
- binarization and thresholds;
- application and dependency versions;
- QC and diagnostic warnings.
