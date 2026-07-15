"""Lightweight GENEActiv/Axivity loading through Oxford accelerometer output.

This module has two paths:
1. Small raw .bin/.cwa files can be converted server-side with accProcess using
   the lightest practical options.
2. Pre-converted accelerometer *timeSeries.csv(.gz) files can be loaded directly
   into pyActigraphy's pandas/BaseRaw workflow. This is the recommended path for
   larger recordings or low-memory Render instances.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import pandas as pd

from .diagnostics import record_diagnostic_event, update_current_stage

try:
    from pyActigraphy.io import BaseRaw
except Exception:  # pragma: no cover - depends on deployment environment
    BaseRaw = None


class AccelerometerProcessingError(ValueError):
    """Raised when accelerometer conversion/loading fails."""


DEFAULT_EPOCH_PERIOD = int(os.environ.get("ACCELEROMETER_EPOCH_PERIOD", "30"))
_DEFAULT_JAVA_HEAP_ENV = os.environ.get("ACCELEROMETER_JAVA_HEAP_MB", "").strip()
DEFAULT_JAVA_HEAP_MB = int(_DEFAULT_JAVA_HEAP_ENV) if _DEFAULT_JAVA_HEAP_ENV else None
MAX_SERVER_SIDE_BIN_MB = float(os.environ.get("MAX_SERVER_SIDE_BIN_MB", "2"))
ACCPROCESS_TIMEOUT_SECONDS = int(os.environ.get("ACCELEROMETER_TIMEOUT_SECONDS", "180"))


def _find_accprocess_executable() -> str:
    executable = shutil.which("accProcess")
    if executable:
        return executable
    raise AccelerometerProcessingError(
        "Raw .bin/.cwa conversion requires the Oxford accelerometer package, but `accProcess` "
        "was not found. Install it with `pip install accelerometer`, or upload a pre-converted "
        "accelerometer timeSeries CSV/CSV.GZ file instead."
    )


def _ensure_java_available() -> None:
    if shutil.which("java"):
        return
    raise AccelerometerProcessingError(
        "Raw .bin/.cwa conversion requires Java because accProcess calls a Java parser. "
        "Install OpenJDK in the backend runtime, or upload a pre-converted accelerometer "
        "timeSeries CSV/CSV.GZ file instead."
    )


def _file_size_mb(path: Path) -> float:
    return path.stat().st_size / (1024 * 1024)


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
        ["time", "timestamp", "datetime", "dateTime", "DateTime", "timeStamp", "date_time"],
    )
    if col is None:
        raise AccelerometerProcessingError(
            "Could not find a timestamp column. Expected a column such as `time`, `timestamp`, "
            f"or `datetime`. Columns found: {list(df.columns)}"
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
        "Could not find an activity/acceleration column. Expected `acc`, `ENMO`, `activity`, or `VM`."
    )


def _pick_light_column(df: pd.DataFrame) -> Optional[str]:
    return _pick_column(df, ["light", "lux", "ambientLight", "light_lux", "LIGHT", "Light"])


def parse_accelerometer_time_column(series: pd.Series) -> pd.Series:
    """Parse accelerometer timestamps such as '...+0100 [Europe/London]'."""
    cleaned = (
        series.astype(str)
        .str.replace(r"\s+\[[^\]]+\]$", "", regex=True)
        .str.strip()
    )
    return pd.to_datetime(cleaned, errors="coerce", utc=True)


def looks_like_accelerometer_timeseries_df(df: pd.DataFrame) -> bool:
    cols = {_normalise_column_name(c) for c in df.columns}
    return "time" in cols and ("acc" in cols or "enmo" in cols or "activity" in cols or "vm" in cols)


def looks_like_accelerometer_timeseries_file(file_path: str, sep: Optional[str] = None) -> bool:
    try:
        df = pd.read_csv(file_path, sep=sep or ",", compression="infer", nrows=5)
        return looks_like_accelerometer_timeseries_df(df)
    except Exception:
        return False


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
            "accProcess ran, but no *timeSeries.csv or *timeSeries.csv.gz output was found. "
            "Try converting locally and upload the generated timeSeries CSV/CSV.GZ file."
        )

    return csv_files[0], json_files[0] if json_files else None


def _read_summary_json(path: Optional[Path]) -> Dict[str, Any]:
    if path is None:
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def build_lightweight_accprocess_command(
    input_path: Path,
    output_dir: Path,
    epoch_period: int = DEFAULT_EPOCH_PERIOD,
    java_heap_mb: Optional[int] = DEFAULT_JAVA_HEAP_MB,
) -> list[str]:
    """Build the lowest-memory accProcess command we can use on a small web server."""
    cmd = [
        _find_accprocess_executable(),
        str(input_path),
        "--outputFolder",
        str(output_dir),
        "--epochPeriod",
        str(epoch_period),
        "--rawOutput",
        "False",
        "--npyOutput",
        "False",
        "--intensityDistribution",
        "False",
        "--m10l5",
        "False",
        "--psd",
        "False",
        "--fourierFrequency",
        "False",
        "--fourierWithAcc",
        "False",
        "--extractFeatures",
        "False",
        "--deleteIntermediateFiles",
        "True",
    ]

    if java_heap_mb and int(java_heap_mb) > 0:
        cmd.append(f"--javaHeapSpace=-Xmx{int(java_heap_mb)}M")

    return cmd


def run_accelerometer_process_lightweight(
    input_path: str,
    epoch_period: int = DEFAULT_EPOCH_PERIOD,
    java_heap_mb: Optional[int] = DEFAULT_JAVA_HEAP_MB,
    max_server_side_mb: float = MAX_SERVER_SIDE_BIN_MB,
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """Convert a small raw .bin/.cwa file with accProcess and return the time series.

    This is intentionally size-limited because Render web services can run out of
    memory during raw accelerometer conversion. Larger files should be converted
    locally and uploaded as *timeSeries.csv.gz.
    """
    source = Path(input_path)
    if not source.exists():
        raise AccelerometerProcessingError(f"Input file does not exist: {source}")

    size_mb = _file_size_mb(source)
    update_current_stage(
        conversion_path="accProcess",
        input_size_mb=round(size_mb, 3),
        max_server_side_mb=max_server_side_mb,
        epoch_period_seconds=epoch_period,
        java_heap_mb=java_heap_mb,
        timeout_seconds=ACCPROCESS_TIMEOUT_SECONDS,
    )
    if size_mb > max_server_side_mb:
        raise AccelerometerProcessingError(
            f"This raw accelerometer file is {size_mb:.2f} MB, which is above the current "
            f"server-side conversion limit of {max_server_side_mb:.2f} MB. To avoid Render "
            "out-of-memory errors, convert the file locally with `accProcess`, then upload the "
            "generated *timeSeries.csv.gz file."
        )

    _ensure_java_available()

    with tempfile.TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir) / "accelerometer_output"
        output_dir.mkdir(parents=True, exist_ok=True)
        cmd = build_lightweight_accprocess_command(
            source,
            output_dir,
            epoch_period=epoch_period,
            java_heap_mb=java_heap_mb,
        )

        update_current_stage(accprocess_command=[str(part) for part in cmd])
        record_diagnostic_event(
            "accprocess_started",
            input_size_mb=round(size_mb, 3),
            epoch_period_seconds=epoch_period,
            java_heap_mb=java_heap_mb,
            timeout_seconds=ACCPROCESS_TIMEOUT_SECONDS,
        )

        try:
            completed = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=False,
                timeout=ACCPROCESS_TIMEOUT_SECONDS,
            )
        except subprocess.TimeoutExpired as exc:
            raise AccelerometerProcessingError(
                "accProcess timed out during lightweight server-side conversion. Convert this file "
                "locally and upload the generated *timeSeries.csv.gz file instead."
            ) from exc

        stdout_tail = completed.stdout[-20000:]
        stderr_tail = completed.stderr[-20000:]
        update_current_stage(
            accprocess_return_code=completed.returncode,
            accprocess_stdout_tail=stdout_tail,
            accprocess_stderr_tail=stderr_tail,
        )
        record_diagnostic_event(
            "accprocess_finished",
            return_code=completed.returncode,
            stdout_tail=stdout_tail[-2000:],
            stderr_tail=stderr_tail[-2000:],
        )

        if completed.returncode != 0:
            if "Could not find or load main class" in stderr_tail and "-Xmx" not in " ".join(cmd):
                hint = " The Java heap argument may be malformed. Use JVM format such as -Xmx256M."
            else:
                hint = ""
            raise AccelerometerProcessingError(
                "accelerometer failed during lightweight conversion. "
                f"{hint} STDOUT: {stdout_tail} STDERR: {stderr_tail}"
            )

        time_series_path, summary_path = _find_accelerometer_outputs(output_dir)
        update_current_stage(
            time_series_output=time_series_path.name,
            time_series_output_mb=round(_file_size_mb(time_series_path), 3),
            summary_output=summary_path.name if summary_path else None,
        )
        df = pd.read_csv(time_series_path, compression="infer")
        summary = _read_summary_json(summary_path)
        update_current_stage(converted_rows=int(len(df)), converted_columns=[str(c) for c in df.columns])
        summary.update(
            {
                "_time_series_output": time_series_path.name,
                "_server_side_conversion": True,
                "_server_side_input_mb": round(size_mb, 3),
                "_epoch_period_seconds": epoch_period,
                "_java_heap_mb": java_heap_mb,
            }
        )
        return df, summary


def load_accelerometer_timeseries_csv(
    file_path: str,
    epoch_period: int = DEFAULT_EPOCH_PERIOD,
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    df = pd.read_csv(file_path, compression="infer")
    if not looks_like_accelerometer_timeseries_df(df):
        raise AccelerometerProcessingError(
            "This CSV does not look like an accelerometer timeSeries file. Expected at least "
            "a `time` column and an `acc`/`ENMO`/`activity`/`VM` column."
        )
    return df, {
        "_server_side_conversion": False,
        "_source": "uploaded_accelerometer_timeseries_csv",
        "_epoch_period_seconds": epoch_period,
    }


def _prepare_timeseries(df: pd.DataFrame, epoch_period: int = DEFAULT_EPOCH_PERIOD):
    time_col = _pick_time_column(df)
    activity_col = _pick_activity_column(df)
    light_col = _pick_light_column(df)

    work = df.copy()
    work.index = parse_accelerometer_time_column(work[time_col])
    work = work.loc[work.index.notna()].sort_index()

    activity = pd.to_numeric(work[activity_col], errors="coerce").dropna()
    if len(activity) < 2:
        raise AccelerometerProcessingError(
            "The accelerometer timeSeries output did not contain enough valid timestamped activity rows."
        )

    inferred_freq = pd.infer_freq(activity.index)
    if inferred_freq is None:
        median_step = pd.Series(activity.index).diff().dropna().median()
        inferred_freq = pd.to_timedelta(median_step) if pd.notna(median_step) else pd.Timedelta(seconds=epoch_period)

    light = None
    if light_col is not None:
        light = pd.to_numeric(work.loc[activity.index, light_col], errors="coerce").rename("light")

    return activity.rename("activity"), light, inferred_freq, str(time_col), str(activity_col), str(light_col) if light_col else None


def summarize_accelerometer_dataframe(
    df: pd.DataFrame,
    summary: Optional[Dict[str, Any]] = None,
    epoch_period: int = DEFAULT_EPOCH_PERIOD,
) -> Dict[str, Any]:
    activity, light, inferred_freq, time_col, activity_col, light_col = _prepare_timeseries(df, epoch_period)
    payload = {
        "rows": int(len(df)),
        "valid_activity_rows": int(len(activity)),
        "columns": [str(c) for c in df.columns],
        "time_column": time_col,
        "activity_column": activity_col,
        "light_column": light_col,
        "start_time": activity.index[0].isoformat(),
        "end_time": activity.index[-1].isoformat(),
        "frequency": str(inferred_freq),
        "activity_mean": float(activity.mean()),
        "activity_min": float(activity.min()),
        "activity_max": float(activity.max()),
        "activity_nonzero_fraction": float((activity > 0).mean()),
        "light_available": light is not None,
        "first_rows": df.head(5).astype(str).to_dict(orient="records"),
        "accelerometer_summary": summary or {},
    }
    if light is not None:
        payload.update(
            {
                "light_mean": float(light.mean()),
                "light_min": float(light.min()),
                "light_max": float(light.max()),
            }
        )
    return payload


def _build_baseraw_from_dataframe(
    df: pd.DataFrame,
    summary: Dict[str, Any],
    name: str,
    epoch_period: int = DEFAULT_EPOCH_PERIOD,
):
    if BaseRaw is None:
        raise AccelerometerProcessingError("pyActigraphy.io.BaseRaw is not available in this backend environment.")

    activity, light, inferred_freq, time_col, activity_col, light_col = _prepare_timeseries(df, epoch_period)

    raw = BaseRaw(
        name=name,
        uuid=str(summary.get("file-deviceID") or summary.get("device") or name),
        format="GENEActiv/accelerometer/Pandas",
        axial_mode=None,
        start_time=activity.index[0],
        period=activity.index[-1] - activity.index[0],
        frequency=inferred_freq,
        data=activity,
        light=light,
    )

    raw._ui_accelerometer_summary = summary
    raw._ui_source_format = "accelerometer_timeseries"
    raw._ui_detected_time_column = time_col
    raw._ui_detected_activity_column = activity_col
    raw._ui_detected_light_column = light_col
    return raw


def load_accelerometer_as_baseraw(
    input_path: str,
    epoch_period: int = DEFAULT_EPOCH_PERIOD,
    java_heap_mb: Optional[int] = DEFAULT_JAVA_HEAP_MB,
):
    """Load a small raw .bin/.cwa file as pyActigraphy BaseRaw via lightweight accProcess."""
    df, summary = run_accelerometer_process_lightweight(
        input_path,
        epoch_period=epoch_period,
        java_heap_mb=java_heap_mb,
    )
    return _build_baseraw_from_dataframe(df, summary, Path(input_path).stem, epoch_period=epoch_period)


def load_accelerometer_csv_as_baseraw(file_path: str, epoch_period: int = DEFAULT_EPOCH_PERIOD):
    """Load an uploaded accelerometer *timeSeries.csv(.gz) file as pyActigraphy BaseRaw."""
    df, summary = load_accelerometer_timeseries_csv(file_path, epoch_period=epoch_period)
    return _build_baseraw_from_dataframe(df, summary, Path(file_path).stem, epoch_period=epoch_period)


def convert_bin_lightweight_summary(
    input_path: str,
    epoch_period: int = DEFAULT_EPOCH_PERIOD,
    java_heap_mb: Optional[int] = DEFAULT_JAVA_HEAP_MB,
) -> Dict[str, Any]:
    df, summary = run_accelerometer_process_lightweight(
        input_path,
        epoch_period=epoch_period,
        java_heap_mb=java_heap_mb,
    )
    return summarize_accelerometer_dataframe(df, summary=summary, epoch_period=epoch_period)


def summarize_uploaded_accelerometer_csv(file_path: str, epoch_period: int = DEFAULT_EPOCH_PERIOD) -> Dict[str, Any]:
    df, summary = load_accelerometer_timeseries_csv(file_path, epoch_period=epoch_period)
    return summarize_accelerometer_dataframe(df, summary=summary, epoch_period=epoch_period)
