"""Statistics for scientific PVGIS/model validation."""
from __future__ import annotations

import numpy as np
import pandas as pd


def regression_statistics(x, y) -> dict[str, float]:
    """Return linear-regression and agreement statistics for finite x/y pairs."""
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    mask = np.isfinite(x) & np.isfinite(y)
    x = x[mask]
    y = y[mask]
    if x.size < 2:
        return {k: np.nan for k in ["n", "slope", "intercept", "r", "r2", "mbe", "mae", "rmse", "mape", "nrmse_pct"]}

    slope, intercept = np.polyfit(x, y, 1)
    if np.std(x) > 0 and np.std(y) > 0:
        r = float(np.corrcoef(x, y)[0, 1])
    else:
        r = np.nan
    residual = y - x
    mbe = float(np.mean(residual))
    mae = float(np.mean(np.abs(residual)))
    rmse = float(np.sqrt(np.mean(residual**2)))
    nonzero = np.abs(x) > 1e-12
    mape = float(np.mean(np.abs(residual[nonzero] / x[nonzero])) * 100.0) if np.any(nonzero) else np.nan
    mean_ref = float(np.mean(np.abs(x)))
    nrmse = 100.0 * rmse / mean_ref if mean_ref > 0 else np.nan
    return {
        "n": int(x.size),
        "slope": float(slope),
        "intercept": float(intercept),
        "r": r,
        "r2": float(r * r) if np.isfinite(r) else np.nan,
        "mbe": mbe,
        "mae": mae,
        "rmse": rmse,
        "mape": mape,
        "nrmse_pct": nrmse,
    }


def error_driver_statistics(frame: pd.DataFrame, error_column: str, parameters: list[str]) -> pd.DataFrame:
    """Linear correlation of independent case parameters with a selected error metric."""
    rows = []
    y = pd.to_numeric(frame[error_column], errors="coerce").to_numpy(dtype=float)
    for parameter in parameters:
        if parameter not in frame.columns:
            continue
        x = pd.to_numeric(frame[parameter], errors="coerce").to_numpy(dtype=float)
        mask = np.isfinite(x) & np.isfinite(y)
        if mask.sum() < 3 or np.nanstd(x[mask]) == 0 or np.nanstd(y[mask]) == 0:
            continue
        slope, intercept = np.polyfit(x[mask], y[mask], 1)
        r = float(np.corrcoef(x[mask], y[mask])[0, 1])
        rows.append({
            "parameter": parameter,
            "n": int(mask.sum()),
            "pearson_r": r,
            "r2": r * r,
            "slope": float(slope),
            "intercept": float(intercept),
            "abs_r": abs(r),
        })
    if not rows:
        return pd.DataFrame(columns=["parameter", "n", "pearson_r", "r2", "slope", "intercept", "abs_r"])
    return pd.DataFrame(rows).sort_values("abs_r", ascending=False).reset_index(drop=True)
