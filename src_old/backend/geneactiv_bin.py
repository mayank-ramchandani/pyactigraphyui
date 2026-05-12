import math
import re
from dataclasses import dataclass
from typing import Dict, List, Optional

import pandas as pd


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

    def RA(self, binarize=True, threshold=4):
        series = self.data.dropna()
        if binarize:
            series = (series > float(threshold)).astype(float)
        l5 = series.rolling("5h", min_periods=1).mean().min()
        m10 = series.rolling("10h", min_periods=1).mean().max()
        return (m10 - l5) / (m10 + l5) if (m10 + l5) != 0 else None

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


def read_raw_geneactiv_bin(file_path: str, resample_freq: str = "1min") -> GeneActivRaw:
    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        lines = [line.strip() for line in f]

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

    for line in lines:
        if line == "Recorded Data":
            break
        match = _KEY_VALUE_RE.match(line)
        if not match:
            continue
        key = match.group(1).strip().lower()
        value = match.group(2).strip()
        header[key] = value
        normalized = key.replace(" ", "_")
        if normalized in calibration:
            calibration[normalized] = _parse_float(value, calibration[normalized])

    records: List[Dict] = []
    i = 0
    while i < len(lines):
        if lines[i] != "Recorded Data":
            i += 1
            continue

        page: Dict[str, str] = {}
        i += 1
        while i < len(lines):
            line = lines[i]
            if not line:
                i += 1
                continue
            if _HEX_RE.match(line) and len(line) >= 12:
                break
            match = _KEY_VALUE_RE.match(line)
            if match:
                page[match.group(1).strip().lower()] = match.group(2).strip()
            i += 1

        hex_data = ""
        while i < len(lines) and lines[i] != "Recorded Data":
            line = lines[i].strip()
            if _HEX_RE.match(line):
                hex_data += line
            i += 1

        page_time = _parse_geneactiv_timestamp(page.get("page time"))
        freq = _parse_float(page.get("measurement frequency"), _parse_float(header.get("measurement frequency"), 1.0)) or 1.0
        if page_time is None or pd.isna(page_time) or not hex_data:
            continue

        n = len(hex_data) // 12
        for sample_idx in range(n):
            decoded = _decode_measurement(hex_data[sample_idx * 12:(sample_idx + 1) * 12], calibration)
            if decoded is None:
                continue
            decoded["timestamp"] = page_time + pd.to_timedelta(sample_idx / freq, unit="s")
            decoded["temperature"] = _parse_float(page.get("temperature"))
            records.append(decoded)

    if not records:
        raise ValueError("This looks like a GENEActiv .bin file, but no page data could be decoded.")

    df = pd.DataFrame(records).set_index("timestamp").sort_index()
    activity = df["enmo"].astype(float)
    light_lux = df["light_lux"].astype(float)
    light_log = light_lux.map(lambda x: math.log10(max(x, 0.0) + 1.0))

    if resample_freq:
        activity = activity.resample(resample_freq).mean().dropna()
        light_lux = light_lux.resample(resample_freq).mean().dropna()
        light_log = light_log.resample(resample_freq).mean().dropna()

    light = SimpleLightRecording({
        "LIGHT": light_log.rename("LIGHT"),
        "LIGHT_LUX": light_lux.rename("LIGHT_LUX"),
    })

    return GeneActivRaw(
        data=activity.rename("ENMO_mg"),
        light=light,
        metadata={"header": header, "samples_decoded": len(df), "resample_freq": resample_freq},
    )
