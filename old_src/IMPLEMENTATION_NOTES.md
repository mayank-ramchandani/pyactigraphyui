# Implemented changes

## Raw file handling

- Added `backend/accelerometer_loader.py`.
- `.bin` files are now routed through the Oxford `accelerometer` package using `accProcess`.
- The generated `*timeSeries.csv(.gz)` output is loaded into a pandas DataFrame and wrapped in `pyActigraphy.io.BaseRaw`.
- `.gt3x` files now return a clear backend message asking the user to export/create an `.agd` file in ActiLife before final pyActigraphy analysis.
- `.agd` files continue to use pyActigraphy native `read_raw_agd`.

## Sleep-window algorithms

- Expanded Crespo_AoT defaults and customizable parameters in `config/algorithmRegistry.json`.
- Expanded Roenneberg_AoT defaults and customizable parameters in `config/algorithmRegistry.json`.
- Added the Roenneberg warning that the method was evaluated for 10-minute binned actigraphy data.
- Updated `backend/analysis.py` so `Roenneberg_AoT` uses the documented `r_consec_below` and `rsfreq` parameters instead of the incorrect `min_period`/`verbose` pair.
- Added advanced onset/offset controls to `components/MetricsPanel.jsx`.

## Requirements

- Added `accelerometer` to backend requirements.
- Removed the direct `pygt3x` dependency from backend requirements because `.gt3x` is not used as the final pyActigraphy analysis route.

## Deployment note

The `accelerometer` package may require Java/OpenJDK in the backend image. If Render fails during `.bin` processing, add OpenJDK to the Docker image or Render build environment.

## Fix for `.bin` error: `No such file or directory: 'java'`

The Oxford `accelerometer` package uses the `java` command during calibration/preprocessing. If `.bin` processing fails with:

```text
Processing failed: [Errno 2] No such file or directory: 'java'
```

the backend environment is missing Java, not the `.bin` file itself.

### Recommended Render deployment

Use the included root-level `Dockerfile` and set the Render backend service language/runtime to **Docker**. The Docker image installs `openjdk-17-jre-headless`, sets `JAVA_HOME`, installs the backend Python dependencies, and starts FastAPI with:

```bash
uvicorn src.backend.app:app --host 0.0.0.0 --port 10000
```

### Local macOS quick fix

```bash
brew install openjdk@17
java -version
```

### Ubuntu/Linux quick fix

```bash
sudo apt-get update
sudo apt-get install -y openjdk-17-jre-headless
java -version
```

The backend now checks for Java before running `accProcess` and returns a clearer error message if Java is missing.
