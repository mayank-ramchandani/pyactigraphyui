# Implementation notes and migration status

This file previously described an early converter-only build and is retained to prevent old repository links from becoming misleading. The current architecture and deployment guidance are maintained in:

- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
- [docs/FILE_FORMATS.md](docs/FILE_FORMATS.md)
- [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)
- [docs/CHANGELOG.md](docs/CHANGELOG.md)

## Current status

- The frontend uses the documented ten-page workflow, with pages 2–9 directly clickable after actigraphy import and Export unlocked after successful result generation.
- Page 2 controls valid-day hours, consecutive-day eligibility, sleep-window coverage, and detected non-wear handling.
- Page 3 offers four activity choices: recommended/automatic, processed acceleration, MAD, and ENMO.
- GENEActiv `.bin` and current-format ActiGraph `.gt3x` use bounded-memory direct readers where supported.
- Axivity `.cwa` and exact Oxford outputs may use the converter/time-series path and can require Java/OpenJDK.
- Current-format GT3X activity is supported directly; it is no longer necessary to export every GT3X recording to `.agd` before analysis.
- Embedded GT3X light is inspected separately from activity using checksum-valid type-`0x05` lux records. No-light files remain valid for activity analysis.
- Crespo and Roenneberg use pyActigraphy-compatible methods with no heuristic fallback window.
- Large activity and light operations use background jobs, progress polling, strict JSON conversion, and structured diagnostics.

Historical statements that GT3X was unsupported, that `pygt3x` had been removed, or that all BIN files must be converted through Java no longer describe this revision.
