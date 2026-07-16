import math
import os
import re
from dataclasses import dataclass
from typing import Dict, List, Optional

import pandas as pd

from .activity_mapping import attach_mapping_metadata, mapping_metadata, normalize_activity_mapping
from .diagnostics import record_diagnostic_event, update_current_stage
import numpy as np

try:
    from scipy.signal import butter, sosfilt, sosfilt_zi
except Exception:  # pragma: no cover
    butter = sosfilt = sosfilt_zi = None


_KEY_VALUE_RE = re.compile(r"^([^:]+):\s*(.*)$")
_HEX_RE = re.compile(r"^[0-9A-Fa-f]+$")


def _parse_float(value, default=None):
    try:
        return float(str(value).strip().split()[0])
    except Exception:
        return default


def _parse_int(value, default=None):
    try:
        return int(float(str(value).strip().split()[0]))
    except Exception:
        return default


def _parse_geneactiv_timestamp(value):
    text = str(value).strip()
    if not text:
        return None
    parts = text.rsplit(":", 1)
    if len(parts) == 2 and parts[1].isdigit() and len(parts[1]) == 3:
        text = parts[0] + "." + parts[1]
    return pd.to_datetime(text, errors="coerce")


def _signed_12bit(value):
    value = int(value)
    return value - 4096 if value >= 2048 else value


def _decode_measurement(hex12: str, calibration: Dict[str, float]):
    if len(hex12) != 12:
        return None
    bits = bin(int(hex12, 16))[2:].zfill(48)
    x_raw = _signed_12bit(int(bits[0:12], 2))
    y_raw = _signed_12bit(int(bits[12:24], 2))
    z_raw = _signed_12bit(int(bits[24:36], 2))
    light_raw = int(bits[36:46], 2)
    button = int(bits[46:47], 2)

    x_gain = calibration.get("x_gain") or 1.0
    y_gain = calibration.get("y_gain") or 1.0
    z_gain = calibration.get("z_gain") or 1.0
    x_offset = calibration.get("x_offset") or 0.0
    y_offset = calibration.get("y_offset") or 0.0
    z_offset = calibration.get("z_offset") or 0.0
    volts = calibration.get("volts") or 1.0
    lux_cal = calibration.get("lux") or 1.0

    x = ((x_raw * 100.0) - x_offset) / x_gain
    y = ((y_raw * 100.0) - y_offset) / y_gain
    z = ((z_raw * 100.0) - z_offset) / z_gain
    lux = light_raw * lux_cal / volts
    vm = math.sqrt((x * x) + (y * y) + (z * z))
    enmo = max(vm - 1.0, 0.0) * 1000.0

    return {
        "x": x,
        "y": y,
        "z": z,
        "vm": vm,
        "enmo": enmo,
        "light_lux": lux,
        "button": button,
    }


def _decode_measurement_array(page_hex: str, calibration: Dict[str, float]):
    """Vectorized decoder for GENEActiv 48-bit samples."""
    usable_len = (len(page_hex) // 12) * 12
    if usable_len <= 0:
        return None, None
    try:
        raw = np.frombuffer(bytes.fromhex(page_hex[:usable_len]), dtype=np.uint8).reshape(-1, 6).astype(np.uint64)
    except Exception:
        return None, None, None

    values = (
        (raw[:, 0] << 40)
        | (raw[:, 1] << 32)
        | (raw[:, 2] << 24)
        | (raw[:, 3] << 16)
        | (raw[:, 4] << 8)
        | raw[:, 5]
    )

    x_raw = ((values >> 36) & 0xFFF).astype(np.int32)
    y_raw = ((values >> 24) & 0xFFF).astype(np.int32)
    z_raw = ((values >> 12) & 0xFFF).astype(np.int32)
    light_raw = ((values >> 2) & 0x3FF).astype(np.float64)

    x_raw = np.where(x_raw >= 2048, x_raw - 4096, x_raw).astype(np.float64)
    y_raw = np.where(y_raw >= 2048, y_raw - 4096, y_raw).astype(np.float64)
    z_raw = np.where(z_raw >= 2048, z_raw - 4096, z_raw).astype(np.float64)

    x_gain = calibration.get("x_gain") or 1.0
    y_gain = calibration.get("y_gain") or 1.0
    z_gain = calibration.get("z_gain") or 1.0
    x_offset = calibration.get("x_offset") or 0.0
    y_offset = calibration.get("y_offset") or 0.0
    z_offset = calibration.get("z_offset") or 0.0
    volts = calibration.get("volts") or 1.0
    lux_cal = calibration.get("lux") or 1.0

    x = ((x_raw * 100.0) - x_offset) / x_gain
    y = ((y_raw * 100.0) - y_offset) / y_gain
    z = ((z_raw * 100.0) - z_offset) / z_gain
    vm = np.sqrt((x * x) + (y * y) + (z * z))
    enmo = np.maximum(vm - 1.0, 0.0) * 1000.0
    light_lux = light_raw * lux_cal / volts
    return enmo, vm, light_lux


class SimpleLightRecording:
    def __init__(self, channels: Dict[str, pd.Series]):
        self._channels = {str(k): v.sort_index().dropna() for k, v in channels.items() if v is not None}
        self.data = pd.concat(self._channels.values(), axis=1) if self._channels else pd.DataFrame()
        if not self.data.empty:
            self.data.columns = list(self._channels.keys())

    def get_channel_list(self):
        return list(self._channels.keys())

    def get_channel(self, channel):
        if channel in self._channels:
            return self._channels[channel]
        lowered = {c.lower(): c for c in self._channels}
        found = lowered.get(str(channel).lower())
        return self._channels.get(found) if found else None

    def _df(self):
        return self.data.copy()

    def light_exposure_level(self, threshold=None, start_time=None, stop_time=None, agg="mean"):
        df = self._df()
        if start_time:
            df = df.loc[pd.to_datetime(start_time):]
        if stop_time:
            df = df.loc[:pd.to_datetime(stop_time)]
        if threshold is not None:
            df = df.where(df >= float(threshold))
        if agg == "median":
            values = df.median()
        elif agg == "max":
            values = df.max()
        elif agg == "min":
            values = df.min()
        elif agg == "sum":
            values = df.sum()
        else:
            values = df.mean()
        return pd.DataFrame({"channel": values.index.astype(str), "value": values.values})

    def summary_statistics_per_time_bin(self, bins="24h", agg_func=None):
        agg_func = agg_func or ["mean", "median", "sum", "std", "min", "max"]
        return self._df().resample(bins).agg(agg_func)

    def TAT(self, threshold=None, start_time=None, stop_time=None, oformat="minute"):
        df = self._df()
        if start_time:
            df = df.loc[pd.to_datetime(start_time):]
        if stop_time:
            df = df.loc[:pd.to_datetime(stop_time)]
        thr = 0.0 if threshold is None else float(threshold)
        counts = (df >= thr).sum()
        freq_seconds = _infer_frequency_seconds(df.index)
        minutes = counts * freq_seconds / 60.0
        if oformat in {"second", "seconds"}:
            values = minutes * 60.0
        elif oformat in {"hour", "hours"}:
            values = minutes / 60.0
        else:
            values = minutes
        return pd.DataFrame({"channel": values.index.astype(str), "value": values.values})

    def TATp(self, threshold=None, start_time=None, stop_time=None, oformat="minute"):
        df = self._df()
        if start_time:
            df = df.loc[pd.to_datetime(start_time):]
        if stop_time:
            df = df.loc[:pd.to_datetime(stop_time)]
        thr = 0.0 if threshold is None else float(threshold)
        freq_seconds = _infer_frequency_seconds(df.index)
        values = (df >= thr).resample("1D").sum() * freq_seconds / 60.0
        if oformat in {"second", "seconds"}:
            values = values * 60.0
        elif oformat in {"hour", "hours"}:
            values = values / 60.0
        return values

    def MLiT(self, threshold=None):
        if threshold is None:
            threshold = 0.0
        df = self._df().where(self._df() >= float(threshold))
        values = df.mean()
        return pd.DataFrame({"channel": values.index.astype(str), "value": values.values})

    def get_light_extremum(self, extremum="max"):
        df = self._df()
        if extremum == "min":
            values = df.min()
        else:
            values = df.max()
        return pd.DataFrame({"channel": values.index.astype(str), "value": values.values})

    def LMX(self, length="5h", lowest=True):
        df = self._df()
        if df.empty:
            return pd.DataFrame(columns=["channel", "value"])
        rolling = df.rolling(length, min_periods=1).mean()
        values = rolling.min() if lowest else rolling.max()
        return pd.DataFrame({"channel": values.index.astype(str), "value": values.values})

    def IS(self, binarize=False, threshold=0):
        return _np_is(self._df(), binarize=binarize, threshold=threshold)

    def IV(self, binarize=False, threshold=0):
        return _np_iv(self._df(), binarize=binarize, threshold=threshold)

    def VAT(self, threshold):
        return (self._df() >= float(threshold)).astype(int)


def _infer_frequency_seconds(index):
    try:
        freq = pd.infer_freq(index[:20])
        if freq:
            return pd.Timedelta(freq).total_seconds()
    except Exception:
        pass
    if len(index) >= 2:
        delta = (index[1] - index[0]).total_seconds()
        if delta > 0:
            return delta
    return 60.0


def _np_is(df, binarize=False, threshold=0):
    work = (df > float(threshold)).astype(float) if binarize else df.astype(float)
    hourly = work.resample("1h").mean().dropna(how="all")
    if hourly.empty:
        return pd.Series(dtype=float, name="IS")
    by_hour = hourly.groupby(hourly.index.hour).mean()
    grand = hourly.mean()
    numerator = ((by_hour - grand) ** 2).sum() * len(hourly)
    denominator = ((hourly - grand) ** 2).sum() * len(by_hour)
    return (numerator / denominator.replace(0, pd.NA)).rename("IS")


def _np_iv(df, binarize=False, threshold=0):
    work = (df > float(threshold)).astype(float) if binarize else df.astype(float)
    hourly = work.resample("1h").mean().dropna(how="all")
    if len(hourly) < 2:
        return pd.Series(dtype=float, name="IV")
    grand = hourly.mean()
    numerator = (hourly.diff().dropna() ** 2).sum() * len(hourly)
    denominator = ((hourly - grand) ** 2).sum() * (len(hourly) - 1)
    return (numerator / denominator.replace(0, pd.NA)).rename("IV")


def _series_frequency(series: pd.Series) -> pd.Timedelta:
    try:
        freq = getattr(series.index, "freq", None)
        if freq is not None:
            return pd.Timedelta(freq)
    except Exception:
        pass
    try:
        inferred = pd.infer_freq(series.index)
        if inferred:
            return pd.Timedelta(inferred)
    except Exception:
        pass
    try:
        diffs = series.index.to_series().diff().dropna()
        if len(diffs):
            return pd.Timedelta(diffs.median())
    except Exception:
        pass
    return pd.Timedelta("1min")


def _average_daily_profile(series: pd.Series, cyclic: bool = True) -> pd.Series:
    """Average epochs by clock time, matching pyActigraphy's L5/M10 basis."""
    series = pd.to_numeric(series, errors="coerce").dropna().sort_index()
    if len(series) == 0 or not isinstance(series.index, pd.DatetimeIndex):
        return pd.Series(dtype=float)
    freq = _series_frequency(series)
    if freq <= pd.Timedelta(0):
        freq = pd.Timedelta("1min")
    time_of_day = series.index - series.index.normalize()
    profile = series.groupby(time_of_day).mean()
    expected_points = max(1, int(round(pd.Timedelta("24h") / freq)))
    expected_index = pd.timedelta_range(start="0s", periods=expected_points, freq=freq)
    profile = profile.reindex(expected_index)
    profile.index.freq = expected_index.freq
    if not cyclic:
        return profile
    second = profile.copy()
    second.index = second.index + pd.Timedelta("24h")
    cyclic_profile = pd.concat([profile, second])
    try:
        cyclic_profile.index.freq = expected_index.freq
    except Exception:
        pass
    return cyclic_profile


def _lmx_from_average_day(series: pd.Series, period: str, lowest: bool = True):
    avgdaily = _average_daily_profile(series, cyclic=True)
    if len(avgdaily) == 0:
        return None, None
    freq = _series_frequency(series)
    n_epochs = max(1, int(pd.Timedelta(period) / freq))
    mean_activity = avgdaily.rolling(period, min_periods=n_epochs).sum().shift(-n_epochs + 1)
    # Start positions after the first 24 h duplicate the same circular windows.
    candidates = mean_activity.loc[mean_activity.index < pd.Timedelta("24h")].dropna()
    if len(candidates) == 0:
        return None, None
    start = candidates.idxmin() if lowest else candidates.idxmax()
    value = float(candidates.loc[start] / n_epochs)
    return start, value


@dataclass
class GeneActivRaw:
    data: pd.Series
    light: SimpleLightRecording
    format: str = "GENEActiv BIN"
    name: str = "GENEActiv"
    metadata: Optional[Dict] = None

    @property
    def white_light(self):
        return self.light.get_channel("LIGHT")

    @property
    def amb_light(self):
        return self.light.get_channel("LIGHT")

    def _activity_series(self):
        series = pd.to_numeric(self.data, errors="coerce").dropna()
        if not isinstance(series.index, pd.DatetimeIndex):
            series.index = pd.to_datetime(series.index, errors="coerce")
            series = series[~pd.isna(series.index)]
        return series.sort_index()

    @property
    def raw_data(self):
        """Unmasked activity series expected by pyActigraphy's Crespo code.

        Native pyActigraphy Raw objects expose both ``data`` and ``raw_data``.
        The streaming GENEActiv reader has no separate mask layer, so the
        decoded epoch series is the appropriate raw-data representation.
        Missing epochs are retained after ``asfreq`` during scoring.
        """
        series = pd.to_numeric(self.data, errors="coerce")
        if not isinstance(series.index, pd.DatetimeIndex):
            series.index = pd.to_datetime(series.index, errors="coerce")
            series = series[~pd.isna(series.index)]
        return series.sort_index()

    def _auto_rest_threshold(self, manual=None):
        if manual not in (None, "", "automatic"):
            try:
                return float(manual)
            except Exception:
                pass
        series = self._activity_series()
        if len(series) == 0:
            return 10.0
        try:
            # ENMO is in mg. The quantile guard adapts to recordings with
            # different dynamic ranges while keeping a practical floor.
            return float(max(10.0, min(50.0, series.quantile(0.30))))
        except Exception:
            return 10.0

    def _rest_score(self, threshold=None):
        series = self._activity_series()
        if len(series) == 0:
            return pd.Series(dtype=float, name="sleep_score")
        threshold = self._auto_rest_threshold(threshold)
        score = (series <= threshold).astype(int)
        score.name = "sleep_score"
        return score

    # These lightweight sleep-scoring fallbacks make directly decoded
    # GENEActiv .bin files usable in the UI even though they are not native
    # pyActigraphy Raw objects. They intentionally return a binary rest/sleep
    # series so downstream TST/WASO/SE code can run instead of failing with
    # missing-method errors.
    def CK(self, settings=None, threshold=None, rescoring=True):
        return self._rest_score(None)

    def Sadeh(self):
        return self._rest_score(None)

    def Scripps(self):
        return self._rest_score(None)

    def Oakley(self, threshold="automatic"):
        return self._rest_score(None if threshold == "automatic" else threshold)

    def resampled_data(self, freq="1min", binarize=False, threshold=4):
        series = self._activity_series().resample(freq).mean()
        if binarize:
            series = (series > float(threshold)).astype(int)
        return series

    @property
    def frequency(self):
        return _series_frequency(self._activity_series())

    def _run_scoring_mixin(self, method_name, *args, **kwargs):
        from pyActigraphy.sleep.scoring_base import ScoringMixin
        method = getattr(ScoringMixin, method_name)
        original_data = self.data
        try:
            series = self._activity_series()
            freq = _series_frequency(series)
            # ScoringMixin algorithms use ``index.freq`` internally. ``asfreq``
            # sets it explicitly and represents real recording gaps as NaN.
            self.data = series.asfreq(freq)
            return method(self, *args, **kwargs)
        finally:
            self.data = original_data

    def Crespo(self, *args, **kwargs):
        # Use the actual pyActigraphy implementation on the streaming-decoded
        # epoch series. GeneActivRaw provides the Raw-like ``data``,
        # ``raw_data``, ``frequency``, and ``resampled_data`` interfaces used by
        # the scoring mixin.
        try:
            return self._run_scoring_mixin("Crespo", *args, **kwargs)
        except Exception:
            # Defensive fallback for environments where pyActigraphy cannot be
            # imported. This is intentionally not used for AoT detection.
            return (self._activity_series() > self._auto_rest_threshold(None)).astype(int)

    def Crespo_AoT(self, *args, **kwargs):
        try:
            return self._run_scoring_mixin("Crespo_AoT", *args, **kwargs)
        except Exception as exc:
            raise RuntimeError(f"pyActigraphy Crespo_AoT could not run on the decoded GENEActiv series: {exc}") from exc

    def Roenneberg(self, *args, **kwargs):
        try:
            return self._run_scoring_mixin("Roenneberg", *args, **kwargs)
        except Exception:
            return self._rest_score(None)

    def Roenneberg_AoT(self, *args, **kwargs):
        try:
            return self._run_scoring_mixin("Roenneberg_AoT", *args, **kwargs)
        except Exception as exc:
            raise RuntimeError(f"pyActigraphy Roenneberg_AoT could not run on the decoded GENEActiv series: {exc}") from exc

    def SleepRegularityIndex(self, algo=None, threshold=None):
        score = self._rest_score(threshold)
        if len(score) == 0:
            return None
        try:
            lag_steps = max(1, int(round(pd.Timedelta("24h").total_seconds() / _infer_frequency_seconds(score.index))))
            if len(score) <= lag_steps:
                return None
            current = score.iloc[lag_steps:]
            previous = score.iloc[:-lag_steps]
            same_state = (current.to_numpy() == previous.to_numpy()).mean()
            return float(same_state * 100.0)
        except Exception:
            return None

    def _transition_probability(self, from_active, to_active, threshold=4):
        series = self._activity_series()
        if len(series) < 2:
            return None
        active = (series > float(threshold)).astype(bool)
        previous = active.shift(1).dropna()
        current = active.loc[previous.index]
        denominator = (previous == bool(from_active)).sum()
        if denominator == 0:
            return None
        numerator = ((previous == bool(from_active)) & (current == bool(to_active))).sum()
        return float(numerator / denominator)

    def kRA(self, threshold=4, start=None, period=None, frac=0.3, it=0, logit=False, freq="1min"):
        # Rest-to-active transition probability fallback.
        return self._transition_probability(False, True, threshold=threshold)

    def kAR(self, threshold=4, start=None, period=None, frac=0.3, it=0, logit=False, freq="1min"):
        # Active-to-rest transition probability fallback.
        return self._transition_probability(True, False, threshold=threshold)

    def L5(self, binarize=True, threshold=4):
        series = self._activity_series()
        if binarize:
            series = (series > float(threshold)).astype(float)
        _start, value = _lmx_from_average_day(series, "5h", lowest=True)
        return value

    def M10(self, binarize=True, threshold=4):
        series = self._activity_series()
        if binarize:
            series = (series > float(threshold)).astype(float)
        _start, value = _lmx_from_average_day(series, "10h", lowest=False)
        return value

    def RA(self, binarize=True, threshold=4):
        series = self._activity_series()
        if binarize:
            series = (series > float(threshold)).astype(float)
        l5_start, l5 = _lmx_from_average_day(series, "5h", lowest=True)
        m10_start, m10 = _lmx_from_average_day(series, "10h", lowest=False)
        denominator = (m10 + l5) if m10 is not None and l5 is not None else None
        value = ((m10 - l5) / denominator) if denominator not in (None, 0) else None
        self._ui_last_ra_components = {
            "method": "pyactigraphy_average_daily_profile_equivalent",
            "binarize": bool(binarize),
            "threshold": float(threshold),
            "l5": l5,
            "m10": m10,
            "l5_start": str(l5_start) if l5_start is not None else None,
            "m10_start": str(m10_start) if m10_start is not None else None,
            "ra": value,
            "ra_at_upper_boundary": bool(value is not None and abs(float(value) - 1.0) < 1e-12),
        }
        return value

    def IS(self, freq="1min", binarize=True, threshold=4):
        df = self.data.rename("activity").to_frame()
        return _np_is(df, binarize=binarize, threshold=threshold).get("activity")

    def IV(self, freq="1min", binarize=True, threshold=4):
        df = self.data.rename("activity").to_frame()
        return _np_iv(df, binarize=binarize, threshold=threshold).get("activity")

    def ISm(self, freqs=None, binarize=True, threshold=4):
        return self.IS(binarize=binarize, threshold=threshold)

    def IVm(self, freqs=None, binarize=True, threshold=4):
        return self.IV(binarize=binarize, threshold=threshold)

    def ISp(self, period="7D", freq="1min", binarize=True, threshold=4, verbose=False):
        return self.data.resample(period).apply(lambda x: GeneActivRaw(x, self.light).IS(binarize=binarize, threshold=threshold))

    def IVp(self, period="7D", freq="1min", binarize=True, threshold=4, verbose=False):
        return self.data.resample(period).apply(lambda x: GeneActivRaw(x, self.light).IV(binarize=binarize, threshold=threshold))

    def RAp(self, period="7D", binarize=True, threshold=4, verbose=False):
        return self.data.resample(period).apply(lambda x: GeneActivRaw(x, self.light).RA(binarize=binarize, threshold=threshold))


def looks_like_geneactiv_bin(file_path: str) -> bool:
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            head = f.read(4000).lower()
    except Exception:
        return False
    return "device type:geneactiv" in head and "recorded data" in head and "page time:" in head


def _add_to_bucket(buckets: Dict[int, Dict[str, float]], bucket_ns: int, decoded: Dict[str, float]) -> None:
    bucket = buckets.setdefault(
        int(bucket_ns),
        {"enmo_sum": 0.0, "light_lux_sum": 0.0, "temperature_sum": 0.0, "count": 0, "temperature_count": 0},
    )
    bucket["enmo_sum"] += float(decoded.get("enmo") or 0.0)
    bucket["light_lux_sum"] += float(decoded.get("light_lux") or 0.0)
    temperature = decoded.get("temperature")
    if temperature is not None:
        bucket["temperature_sum"] += float(temperature)
        bucket["temperature_count"] += 1
    bucket["count"] += 1


def _parse_resample_freq_ns(resample_freq: Optional[str]) -> Optional[int]:
    if not resample_freq:
        return None
    try:
        return int(pd.Timedelta(resample_freq).value)
    except Exception:
        return int(pd.Timedelta("1min").value)


def read_raw_geneactiv_bin(
    file_path: str,
    resample_freq: str = "1min",
    activity_mapping: str = "auto",
) -> GeneActivRaw:
    """Read a GENEActiv .bin file without shelling out to accProcess.

    GENEActiv .bin exports are text-like files containing hex-encoded samples. The
    previous implementation materialized every raw sample before resampling, which
    is risky for participant-sized files. This version streams page-by-page and
    aggregates directly into the requested epoch buckets, so 100+ MB files can be
    previewed/analyzed without hitting the Oxford accProcess size gate.
    """
    requested_mapping = normalize_activity_mapping(activity_mapping)
    if requested_mapping == "mad" and not resample_freq:
        raise ValueError("MAD requires an epoch/resample frequency so within-epoch deviation can be calculated.")

    header: Dict[str, str] = {}
    calibration = {
        "x_gain": 1.0,
        "x_offset": 0.0,
        "y_gain": 1.0,
        "y_offset": 0.0,
        "z_gain": 1.0,
        "z_offset": 0.0,
        "volts": 1.0,
        "lux": 1.0,
    }

    buckets: Dict[int, Dict[str, float]] = {}
    mad_by_bucket: Dict[int, float] = {}
    active_mad_bucket_ns: Optional[int] = None
    active_mad_parts: List[np.ndarray] = []
    rows: List[Dict] = []
    in_header = True
    current_page: Dict[str, str] = {}
    hex_data = ""
    pages_decoded = 0
    samples_decoded = 0
    file_size_bytes = os.path.getsize(file_path)
    bytes_consumed = 0
    resample_ns = _parse_resample_freq_ns(resample_freq)

    acc_filter_sos = None
    acc_filter_zi = None
    acc_filter_freq = None
    acc_filter_expected_next_ns = None
    acc_filter_applied = False
    diagnostic_page_interval = max(1, int(os.getenv("GENEACTIV_DIAGNOSTIC_PAGE_INTERVAL", "5000")))
    update_current_stage(
        parser="direct_geneactiv_streaming_reader",
        resample_freq=resample_freq,
        diagnostic_page_interval=diagnostic_page_interval,
        activity_mapping_requested=requested_mapping,
        file_size_bytes=file_size_bytes,
        progress_message="Decoding raw GENEActiv pages",
    )

    def flush_active_mad_bucket() -> None:
        nonlocal active_mad_bucket_ns, active_mad_parts
        if active_mad_bucket_ns is None or not active_mad_parts:
            active_mad_bucket_ns = None
            active_mad_parts = []
            return
        values = np.concatenate(active_mad_parts).astype(np.float64, copy=False)
        if len(values):
            mean_vm = float(values.mean())
            mad_by_bucket[int(active_mad_bucket_ns)] = float(np.mean(np.abs(values - mean_vm)) * 1000.0)
        active_mad_bucket_ns = None
        active_mad_parts = []

    def add_mad_samples(bucket_ns: int, vm_values: np.ndarray) -> None:
        nonlocal active_mad_bucket_ns, active_mad_parts
        bucket_ns = int(bucket_ns)
        if active_mad_bucket_ns is None:
            active_mad_bucket_ns = bucket_ns
        elif bucket_ns != active_mad_bucket_ns:
            if bucket_ns < active_mad_bucket_ns:
                raise ValueError("GENEActiv pages were not chronological; exact MAD epoch aggregation could not be guaranteed.")
            flush_active_mad_bucket()
            active_mad_bucket_ns = bucket_ns
        active_mad_parts.append(np.asarray(vm_values, dtype=np.float64))

    def processed_acc_values(vm_values: np.ndarray, freq: float, page_ns: int, ns_per_sample: int) -> np.ndarray:
        nonlocal acc_filter_sos, acc_filter_zi, acc_filter_freq
        nonlocal acc_filter_expected_next_ns, acc_filter_applied

        values = np.asarray(vm_values, dtype=np.float64)
        if len(values) == 0:
            return values

        can_filter = butter is not None and sosfilt is not None and sosfilt_zi is not None and float(freq) > 40.0
        if can_filter:
            needs_reset = (
                acc_filter_sos is None
                or acc_filter_freq is None
                or abs(float(acc_filter_freq) - float(freq)) > 1e-6
                or acc_filter_expected_next_ns is None
                or abs(int(page_ns) - int(acc_filter_expected_next_ns)) > max(2 * int(ns_per_sample), 1_000_000)
            )
            if needs_reset:
                acc_filter_sos = butter(4, 20.0, btype="lowpass", fs=float(freq), output="sos")
                acc_filter_zi = sosfilt_zi(acc_filter_sos) * float(values[0])
                acc_filter_freq = float(freq)
            filtered, acc_filter_zi = sosfilt(acc_filter_sos, values, zi=acc_filter_zi)
            acc_filter_applied = True
        else:
            filtered = values

        acc_filter_expected_next_ns = int(page_ns) + len(values) * int(ns_per_sample)
        return np.maximum(filtered - 1.0, 0.0) * 1000.0


    def consume_page(page: Dict[str, str], page_hex: str) -> None:
        nonlocal pages_decoded, samples_decoded
        if not page or not page_hex:
            return

        page_time = _parse_geneactiv_timestamp(page.get("page time"))
        freq = _parse_float(
            page.get("measurement frequency"),
            _parse_float(header.get("measurement frequency"), 1.0),
        ) or 1.0
        if page_time is None or pd.isna(page_time) or freq <= 0:
            return

        page_time = pd.Timestamp(page_time)
        page_ns = int(page_time.value)
        ns_per_sample = int(round(1_000_000_000 / float(freq)))
        temperature = _parse_float(page.get("temperature"))
        enmo_values, vm_values, light_lux_values = _decode_measurement_array(page_hex, calibration)
        if enmo_values is None or vm_values is None or light_lux_values is None or len(enmo_values) == 0:
            return
        use_processed_acc = requested_mapping not in {"mad", "enmo"}
        acc_values = (
            processed_acc_values(vm_values, float(freq), page_ns, ns_per_sample)
            if use_processed_acc
            else enmo_values
        )

        n = len(enmo_values)
        if resample_ns:
            ts_ns = page_ns + (np.arange(n, dtype=np.int64) * ns_per_sample)
            bucket_ids = (ts_ns // resample_ns) * resample_ns
            unique_buckets, inverse = np.unique(bucket_ids, return_inverse=True)
            acc_sums = np.bincount(inverse, weights=acc_values)
            enmo_sums = np.bincount(inverse, weights=enmo_values)
            light_sums = np.bincount(inverse, weights=light_lux_values)
            counts = np.bincount(inverse)

            for idx, bucket_ns in enumerate(unique_buckets):
                bucket = buckets.setdefault(
                    int(bucket_ns),
                    {"acc_sum": 0.0, "enmo_sum": 0.0, "light_lux_sum": 0.0, "temperature_sum": 0.0, "count": 0, "temperature_count": 0},
                )
                bucket["acc_sum"] += float(acc_sums[idx])
                bucket["enmo_sum"] += float(enmo_sums[idx])
                bucket["light_lux_sum"] += float(light_sums[idx])
                bucket["count"] += int(counts[idx])
                if temperature is not None:
                    bucket["temperature_sum"] += float(temperature) * int(counts[idx])
                    bucket["temperature_count"] += int(counts[idx])
                if requested_mapping == "mad":
                    add_mad_samples(int(bucket_ns), vm_values[inverse == idx])
        else:
            for sample_idx in range(n):
                light_lux = float(light_lux_values[sample_idx])
                row = {
                    "timestamp": pd.Timestamp(page_ns + sample_idx * ns_per_sample),
                    "acc": float(acc_values[sample_idx]),
                    "enmo": float(enmo_values[sample_idx]),
                    "light_lux": light_lux,
                    "light_log": math.log10(max(light_lux, 0.0) + 1.0),
                }
                if temperature is not None:
                    row["temperature"] = temperature
                rows.append(row)

        samples_decoded += int(n)
        pages_decoded += 1
        if pages_decoded % diagnostic_page_interval == 0:
            update_current_stage(
                pages_decoded=pages_decoded,
                samples_decoded=samples_decoded,
                resampled_bucket_count=len(buckets),
                bytes_consumed=bytes_consumed,
                file_size_bytes=file_size_bytes,
                progress_fraction=min(0.99, bytes_consumed / file_size_bytes) if file_size_bytes else None,
                progress_message=f"Decoded {pages_decoded:,} GENEActiv pages",
            )
            record_diagnostic_event(
                "geneactiv_parse_progress",
                pages_decoded=pages_decoded,
                samples_decoded=samples_decoded,
                resampled_bucket_count=len(buckets),
            )

    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        for raw_line in f:
            bytes_consumed += len(raw_line.encode("utf-8", errors="ignore"))
            line = raw_line.strip()
            if not line:
                continue

            if line == "Recorded Data":
                if not in_header:
                    consume_page(current_page, hex_data)
                in_header = False
                current_page = {}
                hex_data = ""
                continue

            if in_header:
                match = _KEY_VALUE_RE.match(line)
                if not match:
                    continue
                key = match.group(1).strip().lower()
                value = match.group(2).strip()
                header[key] = value
                normalized = key.replace(" ", "_")
                if normalized in calibration:
                    calibration[normalized] = _parse_float(value, calibration[normalized])
                continue

            if _HEX_RE.match(line):
                hex_data += line
                continue

            match = _KEY_VALUE_RE.match(line)
            if match:
                current_page[match.group(1).strip().lower()] = match.group(2).strip()

    if not in_header:
        consume_page(current_page, hex_data)
    if requested_mapping == "mad":
        flush_active_mad_bucket()

    if resample_ns:
        if not buckets:
            raise ValueError("This looks like a GENEActiv .bin file, but no page data could be decoded.")
        records = []
        for bucket_ns in sorted(buckets):
            bucket = buckets[bucket_ns]
            count = bucket.get("count", 0) or 0
            if count <= 0:
                continue
            light_lux = bucket["light_lux_sum"] / count
            row = {
                "timestamp": pd.Timestamp(bucket_ns),
                "acc": bucket.get("acc_sum", bucket["enmo_sum"]) / count,
                "enmo": bucket["enmo_sum"] / count,
                "mad": mad_by_bucket.get(int(bucket_ns)),
                "light_lux": light_lux,
                "light_log": math.log10(max(light_lux, 0.0) + 1.0),
            }
            temp_count = bucket.get("temperature_count", 0) or 0
            if temp_count > 0:
                row["temperature"] = bucket["temperature_sum"] / temp_count
            records.append(row)
        df = pd.DataFrame(records).set_index("timestamp").sort_index()
    else:
        if not rows:
            raise ValueError("This looks like a GENEActiv .bin file, but no page data could be decoded.")
        df = pd.DataFrame(rows).set_index("timestamp").sort_index()
        df["light_log"] = df["light_lux"].astype(float).map(lambda x: math.log10(max(x, 0.0) + 1.0))

    # Raw GENEActiv files contain calibrated X/Y/Z samples but no native activity-count
    # channel.  The recommended/accelerometer mode therefore uses the streaming,
    # gravity-adjusted epoch-level acceleration series as the common `acc` basis.
    # This avoids materialising hundreds of millions of raw rows for large files.
    if requested_mapping == "mad":
        resolved_mapping = "mad"
        activity = pd.to_numeric(df["mad"], errors="coerce").dropna().rename("MAD_mg")
        if len(activity) < 2:
            raise ValueError("MAD mapping did not produce enough valid GENEActiv epochs.")
    elif requested_mapping == "enmo":
        resolved_mapping = "enmo"
        activity = df["enmo"].astype(float).rename("ENMO_mg")
    else:
        resolved_mapping = "accelerometer"
        activity = df["acc"].astype(float).rename("ACC_mg")

    is_processed_acc = resolved_mapping == "accelerometer"
    activity_mapping_metadata = mapping_metadata(
        requested_mapping,
        resolved_mapping,
        source="direct_geneactiv_streaming_acc",
        processing_engine=(
            "streaming_calibrated_filtered_vm_acc"
            if is_processed_acc
            else f"streaming_custom_{resolved_mapping}"
        ),
        epoch=str(resample_freq),
        calibrated_axes=True,
        vector_magnitude_lowpass_hz=20 if is_processed_acc and acc_filter_applied else None,
        vector_magnitude_filter_order=4 if is_processed_acc and acc_filter_applied else None,
        raw_resampled_to_100_hz=False if is_processed_acc else None,
        available_mappings=["auto", "accelerometer", "mad", "enmo"],
        note=(
            "Large GENEActiv files use a chunked streaming implementation of the epoch-level `acc` basis, "
            "including fourth-order 20 Hz vector-magnitude filtering when the sample rate permits, "
            "to avoid the memory cost of a full raw-data DataFrame. Upload an Oxford accelerometer "
            "*timeSeries.csv.gz file when byte-for-byte accProcess output is required."
            if is_processed_acc
            else "This is an optional custom mapping calculated directly from the calibrated raw samples."
        ),
    )
    light_lux = df["light_lux"].astype(float).rename("LIGHT_LUX")
    light_log = df["light_log"].astype(float).rename("LIGHT")

    light = SimpleLightRecording({
        "LIGHT": light_log,
        "LIGHT_LUX": light_lux,
    })

    update_current_stage(
        pages_decoded=pages_decoded,
        samples_decoded=samples_decoded,
        output_rows=int(len(activity)),
        resample_freq=resample_freq,
        activity_mapping=activity_mapping_metadata,
        bytes_consumed=file_size_bytes,
        file_size_bytes=file_size_bytes,
        progress_fraction=1.0,
        progress_message=f"Decoded {pages_decoded:,} GENEActiv pages into {len(activity):,} epochs",
    )
    record_diagnostic_event(
        "geneactiv_parse_completed",
        pages_decoded=pages_decoded,
        samples_decoded=samples_decoded,
        output_rows=int(len(activity)),
        activity_mapping=activity_mapping_metadata,
    )

    raw = GeneActivRaw(
        data=activity,
        light=light,
        metadata={
            "header": header,
            "pages_decoded": pages_decoded,
            "samples_decoded": samples_decoded,
            "resample_freq": resample_freq,
            "light_channels": {
                "LIGHT": "log10(lux + 1)",
                "LIGHT_LUX": "lux",
            },
            "direct_geneactiv_reader": True,
            "activity_mapping": activity_mapping_metadata,
            "available_activity_mappings": ["auto", "accelerometer", "mad", "enmo"],
        },
    )
    return attach_mapping_metadata(raw, activity_mapping_metadata)

