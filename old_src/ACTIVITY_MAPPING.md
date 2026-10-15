# Activity metric / acceleration-magnitude selection

This compatibility page points to the maintained method description in [docs/ACTIVITY_PROCESSING.md](docs/ACTIVITY_PROCESSING.md).

Page 3 exposes seven activity mappings:

1. `auto` — retain source/device activity when supplied; otherwise use processed epoch-level acceleration for compatible raw XYZ files.
2. `accelerometer` — processed acceleration (`acc`), in mg.
3. `enmo` — epoch mean of positive Euclidean Norm Minus One, in mg.
4. `mad` — mean absolute deviation of vector magnitude, in mg.
5. `pim` — proportional-integrating mode, reported as mg·s/epoch.
6. `zcm` — zero-crossing mode, reported as crossings/epoch.
7. `tat` — time above threshold, reported as seconds/epoch.

ENMO, MAD, PIM, ZCM, and TAT use metric-specific unfiltered raw-signal definitions. ZCM and TAT accept adaptive recording-SD or fixed-mg thresholds; joined source files require one shared fixed threshold.

The resolved mapping, source column or raw-processing engine, units, epoch duration, and preprocessing parameters are retained in preview/results diagnostics. The resulting scalar series is supplied to pyActigraphy-backed metrics and analysis families.
