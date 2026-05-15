"""Load raw GENEActiv/Axivity accelerometer files through Oxford accelerometer.

The pyActigraphy maintainers recommend processing raw .bin/.cwa files with the
Oxford `accelerometer` package first, then using the generated tabular output in
pyActigraphy's pandas/BaseRaw workflow.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import pandas as pd

try:
    from pyActigraphy.io import BaseRaw
except Exception:  # pragma: no cover - depends on deployment environment
    BaseRaw = None


class AccelerometerProcessingError(ValueError):
    """Raised when the external accelerometer conversion step fails."""


def _find_accprocess_executable() -> str:
    executable = shutil.which("accProcess")
    if executable:
        return executable
    raise AccelerometerProcessingError(
        "GENEActiv .bin files must be preprocessed with the Oxford accelerometer package, "
        "but the accProcess command was not found in this backend environment. Install it with "
        "`pip install accelerometer` and ensure accProcess is on PATH."
    )


def _ensure_java_available() -> None:
    if shutil.which("java"):
        return
    raise AccelerometerProcessingError(
        "The Oxford accelerometer package is installed, but Java is missing from this backend "
        "environment. accProcess needs the `java` command during calibration/preprocessing. "
        "Install a Java runtime such as OpenJDK before running .bin/.cwa analysis. For Docker, "
        "add `apt-get install -y openjdk-17-jre-headless` to the backend image. For Render, "
        "deploy the backend with Docker or install OpenJDK in the environment before starting FastAPI."
    )


def _find_accelerometer_outputs(output_dir: Path) -> Tuple[Path, Optional[Path]]:
    csv_files = sorted(
        list(output_dir.rglob("*timeSeries.csv"))
        + list(output_dir.rglob("*timeSeries.csv.gz"))
        + list(output_dir.rglob("*-timeSeries.csv"))
        + list(output_dir.rglob("*-timeSeries.csv.gz"))
    )
    json_files = sorted(
        list(output_dir.rglob("*summary.json"))
        + list(output_dir.rglob("*-summary.json"))
    )

    if not csv_files:
        raise AccelerometerProcessingError(
            "accelerometer ran, but no timeSeries CSV output was found. "
            "Try running accProcess manually on this file to inspect the conversion output."
        )

    return csv_files[0], json_files[0] if json_files else None


def _normalise_column_name(name: Any) -> str:
    return str(name).strip().lower().replace(" ", "").replace("_", "").replace("-", "")


def _pick_column(df: pd.DataFrame, candidates: list[str]) -> Optional[str]:
    lookup = {_normalise_column_name(c): c for c in df.columns}
    for candidate in candidates:
        found = lookup.get(_normalise_column_name(candidate))
        if found is not None:
            return found
    return None


def _pick_time_column(df: pd.DataFrame) -> str:
    col = _pick_column(
        df,
        [
            "time",
            "timestamp",
            "datetime",
            "dateTime",
            "DateTime",
            "timeStamp",
            "date_time",
        ],
    )
    if col is None:
        raise AccelerometerProcessingError(
            "Could not find a timestamp column in the accelerometer timeSeries output. "
            f"Columns found: {list(df.columns)}"
        )
    return col


def _pick_activity_column(df: pd.DataFrame) -> str:
    col = _pick_column(
        df,
        [
            "acc",
            "accOverallAvg",
            "acc_overall_avg",
            "acc-overall-avg",
            "acc-overall-avg(mg)",
            "accImputed",
            "enmo",
            "ENMO",
            "activity",
            "vm",
            "vectorMagnitude",
        ],
    )
    if col is not None:
        return col

    numeric_cols = df.select_dtypes(include="number").columns.tolist()
    if numeric_cols:
        return numeric_cols[0]

    raise AccelerometerProcessingError(
        "Could not find an activity/acceleration column in the accelerometer timeSeries output."
    )


def _pick_light_column(df: pd.DataFrame) -> Optional[str]:
    return _pick_column(
        df,
        [
            "light",
            "lux",
            "ambientLight",
            "light_lux",
            "LIGHT",
            "Light",
        ],
    )


def run_accelerometer_process(
    input_path: str,
    epoch_period: int = 30,
    extra_args: Optional[list[str]] = None,
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """Convert a raw accelerometer file with accProcess and return its time series."""

    source = Path(input_path)
    if not source.exists():
        raise AccelerometerProcessingError(f"Input file does not exist: {source}")

    accprocess = _find_accprocess_executable()
    _ensure_java_available()

    with tempfile.TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir) / "accelerometer_output"
        output_dir.mkdir(parents=True, exist_ok=True)

        cmd = [
            accprocess,
            str(source),
            "--outputFolder",
            str(output_dir),
            "--epochPeriod",
            str(epoch_period),
        ]
        if extra_args:
            cmd.extend(extra_args)

        completed = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False,
        )

        if completed.returncode != 0:
            stdout_tail = completed.stdout[-1500:]
            stderr_tail = completed.stderr[-1500:]
            if "No such file or directory: 'java'" in stdout_tail or "No such file or directory: 'java'" in stderr_tail:
                raise AccelerometerProcessingError(
                    "accelerometer failed because Java is not installed or not available on PATH. "
                    "Install OpenJDK in the backend runtime, then redeploy. "
                    f"STDOUT: {stdout_tail} STDERR: {stderr_tail}"
                )
            raise AccelerometerProcessingError(
                "accelerometer failed to process this file. "
                f"STDOUT: {stdout_tail} "
                f"STDERR: {stderr_tail}"
            )

        time_series_path, summary_path = _find_accelerometer_outputs(output_dir)
        df = pd.read_csv(time_series_path, compression="infer")

        summary: Dict[str, Any] = {}
        if summary_path is not None:
            try:
                with open(summary_path, "r", encoding="utf-8") as f:
                    summary = json.load(f)
            except Exception:
                summary = {}

        summary["_time_series_output"] = str(time_series_path.name)
        return df, summary


def load_accelerometer_as_baseraw(input_path: str, epoch_period: int = 30):
    """Return a pyActigraphy BaseRaw object from a raw .bin/.cwa via accProcess."""

    if BaseRaw is None:
        raise AccelerometerProcessingError(
            "pyActigraphy.io.BaseRaw is not available in this backend environment."
        )

    df, summary = run_accelerometer_process(input_path, epoch_period=epoch_period)

    time_col = _pick_time_column(df)
    activity_col = _pick_activity_column(df)
    light_col = _pick_light_column(df)

    work = df.copy()
    work.index = pd.to_datetime(work[time_col], errors="coerce")
    work = work.loc[work.index.notna()].sort_index()

    activity = pd.to_numeric(work[activity_col], errors="coerce").dropna()
    if len(activity) < 2:
        raise AccelerometerProcessingError(
            "accelerometer output did not contain enough valid timestamped activity rows."
        )

    inferred_freq = pd.infer_freq(activity.index)
    if inferred_freq is None:
        median_step = pd.Series(activity.index).diff().dropna().median()
        if pd.notna(median_step):
            inferred_freq = pd.to_timedelta(median_step)
        else:
            inferred_freq = pd.Timedelta(seconds=epoch_period)

    light = None
    if light_col is not None:
        light = pd.to_numeric(work.loc[activity.index, light_col], errors="coerce")

    raw = BaseRaw(
        name=Path(input_path).stem,
        uuid=str(summary.get("file-deviceID") or summary.get("device") or Path(input_path).stem),
        format="GENEActiv/accelerometer/Pandas",
        axial_mode=None,
        start_time=activity.index[0],
        period=activity.index[-1] - activity.index[0],
        frequency=inferred_freq,
        data=activity.rename("activity"),
        light=light,
    )

    raw._ui_accelerometer_summary = summary
    raw._ui_source_format = "accelerometer_converted"
    raw._ui_detected_activity_column = str(activity_col)
    raw._ui_detected_light_column = str(light_col) if light_col is not None else None
    return raw
