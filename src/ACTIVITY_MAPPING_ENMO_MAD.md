# ENMO and MAD activity options

This compatibility document reflects the current four-option page-3 interface. See [docs/ACTIVITY_PROCESSING.md](docs/ACTIVITY_PROCESSING.md) for the maintained methods description.

- **Recommended / automatic (`auto`)** resolves source/device activity for compatible count-based inputs and processed acceleration for compatible raw acceleration files.
- **Processed acceleration (`accelerometer`)** uses the supported epoch-level `acc` basis.
- **MAD (`mad`)** uses mean amplitude deviation.
- **ENMO (`enmo`)** uses Euclidean Norm Minus One.

Raw GENEActiv `.bin` and current-format ActiGraph `.gt3x` files can be reduced in bounded memory to supported epoch-level activity outputs. Axivity `.cwa` support can depend on the Oxford converter path. A pre-generated Oxford `*timeSeries.csv.gz` can be uploaded when exact release-specific converter output is required.

The old `original` selection is no longer displayed. Automatic mode retains source/device activity when that is the appropriate basis. Always report the resolved basis and units, and do not transfer thresholds across counts, mg, MAD, and ENMO without validation.
