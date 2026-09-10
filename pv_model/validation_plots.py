"""Publication-style matplotlib figures for PVGIS/model validation."""
from __future__ import annotations

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from .validation_statistics import regression_statistics


def _finite_xy(frame: pd.DataFrame, x_col: str, y_col: str):
    x = pd.to_numeric(frame[x_col], errors="coerce").to_numpy(dtype=float)
    y = pd.to_numeric(frame[y_col], errors="coerce").to_numpy(dtype=float)
    mask = np.isfinite(x) & np.isfinite(y)
    return x[mask], y[mask]


def regression_figure(frame, x_col, y_col, x_label, y_label, title, one_to_one=True):
    x, y = _finite_xy(frame, x_col, y_col)
    stats = regression_statistics(x, y)
    fig, ax = plt.subplots(figsize=(7.2, 5.4))
    ax.scatter(x, y, s=34, alpha=0.75, edgecolors="none", label="Benchmark cases")
    if len(x) >= 2:
        xline = np.linspace(float(np.min(x)), float(np.max(x)), 200)
        ax.plot(xline, stats["intercept"] + stats["slope"] * xline, linewidth=2.0, label="Linear regression")
        if one_to_one:
            low = min(float(np.min(x)), float(np.min(y)))
            high = max(float(np.max(x)), float(np.max(y)))
            ax.plot([low, high], [low, high], linestyle="--", linewidth=1.5, label="1:1 reference")
    text = (
        f"n = {int(stats['n']) if np.isfinite(stats['n']) else 0}\n"
        f"y = {stats['slope']:.4f} x {stats['intercept']:+.2f}\n"
        f"R² = {stats['r2']:.4f}\n"
        f"r = {stats['r']:.4f}\n"
        f"RMSE = {stats['rmse']:.2f}\n"
        f"MAPE = {stats['mape']:.2f} %"
    )
    ax.text(0.03, 0.97, text, transform=ax.transAxes, va="top", ha="left", fontsize=9,
            bbox={"boxstyle": "round", "facecolor": "white", "alpha": 0.85})
    ax.set_xlabel(x_label)
    ax.set_ylabel(y_label)
    ax.set_title(title)
    ax.grid(True, alpha=0.25)
    ax.legend(loc="lower right", fontsize=9)
    fig.tight_layout()
    return fig


def error_driver_figure(frame, x_col, error_col, x_label, error_label, title):
    x, y = _finite_xy(frame, x_col, error_col)
    fig, ax = plt.subplots(figsize=(7.2, 5.0))
    ax.scatter(x, y, s=32, alpha=0.75, edgecolors="none")
    if len(x) >= 2 and np.std(x) > 0:
        slope, intercept = np.polyfit(x, y, 1)
        r = float(np.corrcoef(x, y)[0, 1]) if np.std(y) > 0 else np.nan
        xline = np.linspace(float(np.min(x)), float(np.max(x)), 200)
        ax.plot(xline, intercept + slope * xline, linewidth=2.0, label=f"Regression: r={r:.3f}, R²={r*r:.3f}")
        ax.legend(fontsize=9)
    ax.axhline(0.0, linestyle="--", linewidth=1.2)
    ax.set_xlabel(x_label)
    ax.set_ylabel(error_label)
    ax.set_title(title)
    ax.grid(True, alpha=0.25)
    fig.tight_layout()
    return fig


def error_distribution_figure(frame, error_col="energy_error_pct"):
    values = pd.to_numeric(frame[error_col], errors="coerce").dropna().to_numpy(dtype=float)
    fig, ax = plt.subplots(figsize=(7.2, 4.8))
    ax.hist(values, bins=15, alpha=0.8, edgecolor="white")
    if len(values):
        ax.axvline(float(np.mean(values)), linewidth=2.0, label=f"Mean = {np.mean(values):.2f} %")
        ax.axvline(float(np.median(values)), linestyle="--", linewidth=1.8, label=f"Median = {np.median(values):.2f} %")
    ax.set_xlabel("Relative energy error [%]")
    ax.set_ylabel("Number of cases")
    ax.set_title("Distribution of relative model error")
    ax.grid(True, axis="y", alpha=0.25)
    ax.legend(fontsize=9)
    fig.tight_layout()
    return fig


def bland_altman_figure(frame, reference_col="pvgis_energy_kwh_a", model_col="model_energy_kwh_a"):
    reference, model = _finite_xy(frame, reference_col, model_col)
    mean_pair = (reference + model) / 2.0
    diff = model - reference
    bias = float(np.mean(diff)) if len(diff) else np.nan
    sd = float(np.std(diff, ddof=1)) if len(diff) > 1 else np.nan
    loa_low = bias - 1.96 * sd if np.isfinite(sd) else np.nan
    loa_high = bias + 1.96 * sd if np.isfinite(sd) else np.nan
    fig, ax = plt.subplots(figsize=(7.2, 5.0))
    ax.scatter(mean_pair, diff, s=34, alpha=0.75, edgecolors="none")
    if np.isfinite(bias):
        ax.axhline(bias, linewidth=2.0, label=f"Bias = {bias:.1f} kWh/a")
    if np.isfinite(loa_low):
        ax.axhline(loa_low, linestyle="--", linewidth=1.3, label=f"95% LoA = {loa_low:.1f} … {loa_high:.1f} kWh/a")
        ax.axhline(loa_high, linestyle="--", linewidth=1.3)
    ax.set_xlabel("Mean of PVGIS and model energy [kWh/a]")
    ax.set_ylabel("Model − PVGIS [kWh/a]")
    ax.set_title("Bland–Altman agreement plot")
    ax.grid(True, alpha=0.25)
    ax.legend(fontsize=9)
    fig.tight_layout()
    return fig
