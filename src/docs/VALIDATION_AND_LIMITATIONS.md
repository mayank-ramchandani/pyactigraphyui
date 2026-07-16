# Validation and limitations

## Computation is not validation

A metric completing without an exception establishes only that the implementation returned a result. It does not establish that the selected device, activity mapping, thresholds, algorithm, and population form a validated scientific method.

## Golden-file test collection

Maintain a permanent set containing:

- a small known-good file;
- a medium file;
- a large raw file;
- a recording with gaps;
- a recording with light channels;
- a recording without light channels;
- files where Crespo and Roenneberg are known to return windows;
- a previously failing file;
- examples from each supported device/format.

Store expected values, tolerances, dependency versions, checksums, and diagnostic reports.

## Required comparison layers

For each important file, compare:

1. direct local Python processing;
2. processing inside the production container image;
3. processing through the public web endpoint.

This distinguishes analysis-code failures from container, proxy, and upload failures.

## Known limitations

### Processed acceleration

The direct chunked pathway follows the intended filtered, gravity-adjusted vector-magnitude sequence but may not reproduce every Oxford `accProcess` release byte-for-byte. Upload a generated `timeSeries.csv.gz` when release-specific equivalence is required.

### Activity scales

Device counts, processed `acc`, MAD, and ENMO have different distributions and units. Thresholds and published cut points cannot be transferred without justification.

### Sleep algorithms

Classic sleep algorithms and AoT procedures may execute on a generic activity series without being validated for that exact mapping. Treat unvalidated combinations as exploratory and report the complete processing method.

### Missingness and non-wear

Masked or missing intervals should not be interpreted as zero activity. Long gaps can alter daily profiles, transition probabilities, sleep windows, and rhythm metrics.

### Large-file infrastructure

Success depends on:

- proxy upload limits;
- backend worker count;
- memory limit;
- temporary storage;
- request duration;
- Java heap for converter paths;
- concurrent analyses;
- replica routing for progress polling.

### Boundary values

RA = 1 is mathematically valid when L5 = 0. Other metrics may return vectors, empty arrays, NaN, or infinity. API responses convert non-finite values to `null` and retain diagnostics.

## Release acceptance checklist

Before promoting a build:

- confirm `/api/version` and commit ID;
- compile all Python modules;
- bundle the frontend;
- run golden-file tests;
- test partial metric failure;
- test a vector-returning metric (`ISp`, `IVp`, or `RAp`);
- test Crespo and Roenneberg;
- test upload/progress reporting;
- test diagnostic JSON download;
- test a file near the production upload-size limit;
- review methods and change-log documentation.
