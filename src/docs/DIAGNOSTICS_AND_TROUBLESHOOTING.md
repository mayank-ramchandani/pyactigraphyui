# Troubleshooting

Results, quality-control messages, and per-stage statuses appear on **Step 9: Generate Results**. Use this guide to decide what to review or retry.

## Status meanings

| Status | Meaning | User action |
|---|---|---|
| Passed | The stage completed normally | No action is required |
| Warning | Processing continued, but a value or quality issue needs review | Read the message and confirm whether the output is suitable |
| Failed | The stage could not produce a usable result | Review the file, selected settings, and exact error |
| Skipped | A required signal, window, or supported method was unavailable | Confirm that the necessary data and settings were supplied |
| Completed with warnings | Results were returned, but one or more issues require review | Do not ignore the warnings when interpreting or reporting results |

## First checks after a problem

1. Confirm that the correct file and activity measure were selected.
2. Review the activity preview for gaps, zeros, date problems, or an unexpectedly short recording.
3. Review daily quality, valid-window counts, and the longest consecutive run.
4. Review sleep-window coverage when a sleep metric is missing.
5. Retry once with one file and only the essential metrics.
6. Record the request ID and exact message if the problem repeats.

## Common messages

### File too large or HTTP 413

The upload was rejected before processing began. Try a smaller file when possible. When contacting the service team, include the file format, file size, workflow step, and exact message.

### HTTP 500, 503, or 504

The service encountered an error, timeout, or temporary interruption. Retry once, preferably with one file. If the error repeats, submit feedback with the request ID, filename, file size, selected activity measure, and exact message.

### Background job not found

The saved preview or analysis job is no longer available. Start the operation again and keep the page open during processing. Avoid refreshing, closing the tab, or starting several large jobs at once.

### No light data

No usable light channel was found. This does not prevent activity analysis. Upload a separate light file only when light outcomes are required.

### CSV encoding or column-detection problem

For older or localized CSV files, confirm that the current application version is being used. Enable manual CSV mapping and select the correct timestamp, activity, light, temperature, and non-wear columns.

### NHANES PAXHR_H has no timestamp

PAXHR_H contains hourly summaries for many participants. Prepare one participant at a time and construct a documented participant-relative time index before mapping PAXMTSH as activity.

### Metric is unavailable or null

Review whether the metric requires:

- more valid data;
- a longer consecutive valid-window run;
- a sleep window;
- higher sleep-window coverage;
- a supported activity signal;
- a compatible threshold or parameter.

The unavailable-result message should identify the main reason.

### RA equals 1

RA equals 1 when L5 is zero and M10 is positive. Review M10 and L5, their timing, the activity measure and units, thresholding, gaps, non-wear, and masks before interpreting the value.

### Crespo_AoT or Roenneberg_AoT finds no window

The selected method did not find a usable main rest interval. Review recording duration, gaps, wear time, the activity measure, and the detected onset/offset information. A no-window result does not prove that no sleep occurred. Use a diary-defined window when one is available.

### Sleep metrics are excluded for low coverage

The sleep interval did not retain enough scorable epochs after gaps, non-wear, start/stop limits, and masks. Review the sleep-window quality table. Change the threshold only when justified by the protocol or a planned sensitivity analysis.

## Submitting useful feedback

Include:

- workflow step;
- affected filename and format;
- file size;
- selected activity measure;
- selected sleep algorithm or metric, when relevant;
- request ID;
- exact visible message;
- whether the problem repeats with one file.

Do not include participant identifiers, raw measurements, or other sensitive information in the feedback text. A contact email is required so the team can follow up. Feedback and attached technical context are retained for 30 days.
