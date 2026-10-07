# ENMO, MAD, PIM, ZCM, and TAT activity options

This compatibility document points to [docs/ACTIVITY_PROCESSING.md](docs/ACTIVITY_PROCESSING.md) for the maintained preprocessing description.

- **ENMO (`enmo`)**: epoch mean of positive Euclidean Norm Minus One.
- **MAD (`mad`)**: mean absolute deviation of vector magnitude within the epoch.
- **PIM (`pim`)**: integral of unfiltered `|VM - 1 g|` within the epoch.
- **ZCM (`zcm`)**: crossings of a positive threshold in unfiltered `|VM - 1 g|` within the epoch.
- **TAT (`tat`)**: seconds above a positive threshold in unfiltered `|VM - 1 g|` within the epoch.

Raw GENEActiv `.bin` and ActiGraph `.gt3x` recordings use bounded-memory streaming reducers. Adaptive ZCM/TAT performs one streaming SD-estimation pass and one calculation pass. Preprocessed time-series files can supply existing ENMO, MAD, PIM, ZCM, or TAT columns directly. Actiwatch ATR PIM/ZCM/TAT selections are passed to pyActigraphy's native reader modes.

Implementation rationale: [Maczák et al. (2021)](https://doi.org/10.1371/journal.pone.0261718).
