# ENMO, MAD, PIM, and ZCM activity options

This compatibility document points to [docs/ACTIVITY_PROCESSING.md](docs/ACTIVITY_PROCESSING.md) for the maintained preprocessing description.

- **ENMO (`enmo`)**: epoch mean of positive Euclidean Norm Minus One.
- **MAD (`mad`)**: mean absolute deviation of vector magnitude within the epoch.
- **PIM (`pim`)**: integral of absolute dynamic vector magnitude within the epoch.
- **ZCM (`zcm`)**: dead-band zero-crossing count of dynamic vector magnitude within the epoch.

Raw GENEActiv `.bin` and ActiGraph `.gt3x` recordings use bounded-memory streaming reducers. Preprocessed time-series files can supply existing ENMO, MAD, PIM, or ZCM columns directly. Actiwatch ATR PIM/ZCM selections are passed to pyActigraphy's native reader modes.
