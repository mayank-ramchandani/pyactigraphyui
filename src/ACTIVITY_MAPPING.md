# Activity metric / acceleration-magnitude selection

This top-level file is retained for compatibility with older repository links. The current detailed documentation is [docs/ACTIVITY_PROCESSING.md](docs/ACTIVITY_PROCESSING.md).

The setting appears on **page 3: Estimating Activity Metric / Magnitude of Acceleration** and has four public choices:

1. `auto` — recommended/automatic. Preserve a suitable source/device activity series when present; otherwise resolve an appropriate processed acceleration basis for compatible raw X/Y/Z files.
2. `accelerometer` — explicitly request processed epoch-level acceleration (`acc`), typically reported in mg.
3. `mad` — mean amplitude deviation, reported in mg when derived from calibrated acceleration.
4. `enmo` — Euclidean Norm Minus One, using the application's documented custom ENMO implementation/available source column.

There is no separate `original` button in the current UI. Source/device activity remains reachable through `auto` for compatible count-based or native files. The requested and resolved basis, engine, source column, units, and epoch are recorded in preview/results diagnostics.

Page 4 previews activity using the selected initial basis, while page 8 controls metric selection and page 9 runs the analysis. Thresholds defined on a count scale must not be assumed equivalent to mg-scale processed acceleration, MAD, or ENMO.
