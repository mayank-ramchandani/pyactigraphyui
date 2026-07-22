# Metrics and algorithms

The metric and algorithm registries are the machine-readable source for labels, descriptions, default parameters, and backend method names:

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
| ISp / IVp / RAp | Period-specific outputs that may be vectors rather than scalar values. |

### Relative amplitude

```text
RA = (M10 - L5) / (M10 + L5)
```

An RA of exactly 1 is mathematically possible when L5 is zero and M10 is positive. Interpretation requires reviewing:

- M10 and L5 values;
- M10/L5 start times;
- activity basis and units;
- binarization and threshold;
- missing-data and masking decisions.

## Fragmentation metrics

| Metric | Meaning |
|---|---|
| kRA | Transition probability from rest to activity under the selected threshold/scoring setup. |
| kAR | Transition probability from activity to rest under the selected threshold/scoring setup. |

Availability can depend on the raw-object interface and the selected activity scale.

## Sleep metrics

| Metric | Meaning |
|---|---|
| SRI | Sleep Regularity Index over the available scored series. |
| TST | Total sleep time within selected windows. |
| WASO | Wake after sleep onset within a usable rest/sleep window. |
| Sleep efficiency | Proportion of the selected interval classified as sleep/rest. |

These metrics require a scored rest/activity series and, for window-dependent summaries, usable intervals.

## Epoch-by-epoch algorithms

The registry currently includes:

- Cole-Kripke;
- Sadeh;
- Oakley;
- Scripps;
- Crespo;
- Roenneberg.

The classic scoring algorithms were developed with specific devices, count scales, epochs, placements, and populations. Executing them on a generic mg series does not establish validation for that combination.

## Crespo and Roenneberg window detection

Crespo and Roenneberg estimate rest/activity structure and return onset/offset arrays. The application:

- calls the actual pyActigraphy methods through a Raw-like adapter;
- validates onset/offset pairs;
- filters windows using configured minimum and maximum durations;
- records method, parameters, count, notes, and exceptions;
- does not insert a fallback window.

A valid recording can return no usable windows because of:

- insufficient day/night contrast;
- long gaps or non-wear;
- a short recording;
- constant or near-zero activity;
- inappropriate activity scale or thresholds;
- resampling or parameter choices;
- windows outside the configured duration range.

Roenneberg should generally be evaluated with 10-minute resampling as the starting configuration.

## Reporting requirements

Every reported result should include:

- file ID and source filename;
- device/file format;
- requested and resolved activity basis;
- units and epoch duration;
- mask and analysis intervals;
- algorithm and parameters;
- binarization and threshold;
- application and dependency versions;
- QC and diagnostic warnings.
