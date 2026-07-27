import sys
import types
import unittest
from unittest.mock import patch

import numpy as np
import pandas as pd

from backend.analysis import _run_cosinor_family


class _FakeParameter:
    def __init__(self, value):
        self.value = value

    def set(self, value=None, **_kwargs):
        if value is not None:
            self.value = value


class _FakeParameters(dict):
    def copy(self):
        return _FakeParameters({key: _FakeParameter(value.value) for key, value in self.items()})

    def valuesdict(self):
        return {key: value.value for key, value in self.items()}


class _FakeCosinor:
    def __init__(self):
        self.fit_initial_params = _FakeParameters({
            "Amplitude": _FakeParameter(50.0),
            "Acrophase": _FakeParameter(np.pi),
            "Period": _FakeParameter(1440.0),
            "Mesor": _FakeParameter(50.0),
        })

    def fit(self, ts, params, **_kwargs):
        self.received = ts
        params["Mesor"].value = 10.0
        params["Amplitude"].value = 3.0
        params["Acrophase"].value = np.pi
        return types.SimpleNamespace(
            params=params,
            success=True,
            bic=123.4,
            redchi=2.5,
        )


class CosinorFamilyTests(unittest.TestCase):
    def test_fixed_24_hour_pyactigraphy_cosinor_result(self):
        analysis_module = types.ModuleType("pyActigraphy.analysis")
        analysis_module.Cosinor = _FakeCosinor
        raw = types.SimpleNamespace(
            data=pd.Series(
                np.arange(48, dtype=float),
                index=pd.date_range("2026-01-01", periods=48, freq="1h"),
            )
        )

        with patch.dict(sys.modules, {"pyActigraphy.analysis": analysis_module}):
            result = _run_cosinor_family(raw)

        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["model"], "single_component_fixed_24_hour")
        self.assertEqual(result["mesor"], 10.0)
        self.assertEqual(result["amplitude"], 3.0)
        self.assertAlmostEqual(result["period_hours"], 24.0)
        self.assertAlmostEqual(result["peak_offset_hours"], 12.0)
        self.assertEqual(result["peak_clock_time"], "12:00:00")
        self.assertEqual(result["pyactigraphy_class"], "pyActigraphy.analysis.Cosinor")

    def test_requires_about_one_day_of_valid_epochs(self):
        analysis_module = types.ModuleType("pyActigraphy.analysis")
        analysis_module.Cosinor = _FakeCosinor
        raw = types.SimpleNamespace(
            data=pd.Series(
                np.arange(12, dtype=float),
                index=pd.date_range("2026-01-01", periods=12, freq="1h"),
            )
        )

        with patch.dict(sys.modules, {"pyActigraphy.analysis": analysis_module}):
            result = _run_cosinor_family(raw)

        self.assertEqual(result["status"], "insufficient_data")
        self.assertEqual(result["required_epochs"], 24)


if __name__ == "__main__":
    unittest.main()
