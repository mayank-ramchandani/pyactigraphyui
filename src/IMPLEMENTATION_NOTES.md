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

## Lightweight Render-safe .bin/.cwa handling update

Raw GENEActiv/Axivity conversion through Oxford `accelerometer` can exceed memory on small Render web services because it launches Java and produces intermediate data. This build uses a safer default:

- Raw `.bin`/`.cwa` server-side conversion is size-limited by `MAX_SERVER_SIDE_BIN_MB` (default: `2`).
- Java heap is capped with JVM syntax: `--javaHeapSpace -Xmx256M` by default through `ACCELEROMETER_JAVA_HEAP_MB=256`.
- Expensive outputs/features are disabled for server conversion: `--extractFeatures False`, `--rawOutput False`, `--npyOutput False`, `--m10l5 False`, `--psd False`, Fourier outputs off.
- Larger raw files should be converted locally with `accProcess`, then the generated `*timeSeries.csv.gz` should be uploaded to the app.
- Uploaded accelerometer `timeSeries.csv`/`timeSeries.csv.gz` files are now detected directly using the columns `time` + `acc`/`ENMO`/`activity`/`VM`.

Diagnostic endpoint:

```bash
curl -X POST "$BACKEND_URL/api/accelerometer/convert-lite" \
  -F "file=@TESTfile.bin" \
  -F "epochPeriod=30" \
  -F "javaHeapMb=256"
```

For larger files, convert locally:

```bash
accProcess recording.bin --outputFolder acc_output --epochPeriod 30
```

Then upload the generated `*-timeSeries.csv.gz` file to the usual preview/analyze endpoints, or test it with:

```bash
curl -X POST "$BACKEND_URL/api/accelerometer/convert-lite" \
  -F "file=@recording-timeSeries.csv.gz" \
  -F "epochPeriod=30"
```
