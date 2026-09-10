from pathlib import Path
import importlib.util
import numpy as np
import pandas as pd

PATH = Path(__file__).parents[1] / "pv_model" / "validation_statistics.py"
spec = importlib.util.spec_from_file_location("validation_statistics_standalone", PATH)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def test_regression_exact_line():
    x = np.array([1., 2., 3., 4.])
    y = 2.0 * x + 3.0
    s = mod.regression_statistics(x, y)
    assert abs(s["slope"] - 2.0) < 1e-12
    assert abs(s["intercept"] - 3.0) < 1e-12
    assert abs(s["r2"] - 1.0) < 1e-12


def test_agreement_metrics_identity():
    x = np.array([10., 20., 30.])
    s = mod.regression_statistics(x, x)
    assert s["mbe"] == 0.0
    assert s["mae"] == 0.0
    assert s["rmse"] == 0.0
    assert s["mape"] == 0.0


def test_error_driver_ranking():
    f = pd.DataFrame({"err": [0, 1, 2, 3, 4], "strong": [0, 1, 2, 3, 4], "weak": [2, 0, 4, 1, 3]})
    out = mod.error_driver_statistics(f, "err", ["strong", "weak"])
    assert out.iloc[0]["parameter"] == "strong"
    assert abs(out.iloc[0]["pearson_r"] - 1.0) < 1e-12
