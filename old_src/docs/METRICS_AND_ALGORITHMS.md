# Metrics and algorithms

Sleep-window and classification choices are made on **Step 6**. Analysis families and individual metrics are selected on **Step 8**. Results are generated on **Step 9**.

## Analysis families

| Family | Included outputs | What it describes |
|---|---|---|
| Amplitude | RA and period-specific RA | Difference between the most and least active parts of the day |
| Rhythm | IS, IV, and related mean/period-specific forms | Day-to-day stability and within-day fragmentation |
| Sleep | SRI, TST, WASO, sleep efficiency | Sleep timing, duration, continuity, and regularity |
| Fragmentation | kRA and kAR | Transitions between rest and activity states |
| Cosinor | Mesor, amplitude, acrophase, fit statistics | A fitted 24-hour rhythmic pattern |

Additional advanced families may appear in the interface. Review their availability and output status before using them.

## Rest-activity metrics

| Metric | Meaning |
|---|---|
| RA | Relative amplitude between the most active 10 hours (M10) and least active 5 hours (L5) of the average day |
| IS | Interdaily stability: repeatability of the 24-hour activity pattern across days |
| IV | Intradaily variability: fragmentation or transitions within the day |
| ISm / IVm | Mean forms calculated across multiple resampling frequencies |
| ISp / IVp / RAp | Period-specific values that may contain multiple outputs |

### Relative amplitude

`RA = (M10 - L5) / (M10 + L5)`

RA can equal 1 when L5 is zero and M10 is positive. Before interpreting an extreme value, review M10 and L5, their start times, the activity measure and units, binarization, thresholds, gaps, non-wear, and masks.

## Fragmentation metrics

| Metric | Meaning |
|---|---|
| kRA | Rest-to-activity transition probability summary |
| kAR | Activity-to-rest transition probability summary |

Fragmentation measures depend on the active/rest classification settings. Confirm that the threshold and signal units are appropriate.

## Sleep metrics

| Metric | Meaning |
|---|---|
| SRI | Similarity of sleep/wake state at the same time on consecutive days |
| TST | Total sleep time within the analysed sleep window |
| WASO | Wake time after sleep onset within the analysed sleep window |
| Sleep efficiency | Proportion of the sleep interval scored as sleep |

Sleep metrics require a usable sleep window and enough scorable coverage. SRI also requires valid 24-hour epoch pairs.

## Sleep/rest algorithms

| Algorithm | Typical context | Important note |
|---|---|---|
| Cole-Kripke | Adult actigraphy | Common adult epoch-by-epoch rest/activity scoring option |
| Sadeh | Pediatric and adolescent actigraphy | Often used in younger populations |
| Oakley | Actiware-related workflows | Confirm compatibility with the selected activity scale |
| Scripps | Additional comparison scoring | Useful when comparing several scoring approaches |
| Crespo | Pattern-based rest/activity detection | Crespo_AoT can estimate a main rest window when no diary is available |
| Roenneberg | Trend-based consolidated-rest detection | Roenneberg_AoT can estimate a main nocturnal rest interval |

No lowest-activity fallback window is inserted when Crespo_AoT or Roenneberg_AoT returns no usable onset and offset.

## Why a metric may be unavailable

A metric can be unavailable because:

- the recording does not contain enough valid data;
- the longest consecutive valid-window run is too short;
- a required sleep window is missing or below the coverage threshold;
- the selected signal or file format does not support the calculation;
- a metric-specific parameter could not be applied;
- the algorithm returned no usable result.

Review the quality tables and the metric-specific message before changing settings.

## Reporting

Keep the following with each result:

- metric or analysis family;
- activity measure and units;
- epoch duration;
- continuous or binarized processing and threshold;
- sleep window source and classification algorithm;
- metric-specific parameters;
- valid-window and sleep-window coverage settings;
- warnings and unavailable-result reasons.
