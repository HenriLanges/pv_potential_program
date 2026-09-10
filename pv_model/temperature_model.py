"""Faiman temperature model and temperature-dependent module efficiency."""

from __future__ import annotations

import numpy as np


def calculate_cell_temperature(
    irradiance_wm2: np.ndarray,
    ambient_temperature_c: np.ndarray,
    wind_speed_mps: np.ndarray,
    u0_wm2k: float = 25.0,
    u1_wm2k_per_mps: float = 6.84,
) -> np.ndarray:
    """Calculate module/cell temperature with the Faiman model.

    T_mod = T_amb + G_POA / (U0 + U1 * v_wind)

    Wind speed is taken from PVGIS ``WS10m`` in this project. The model is kept
    intentionally simple and does not convert wind speed to another measurement height.
    """
    irradiance = np.maximum(np.asarray(irradiance_wm2, dtype=float), 0.0)
    ambient = np.asarray(ambient_temperature_c, dtype=float)
    wind_speed = np.maximum(np.asarray(wind_speed_mps, dtype=float), 0.0)

    if irradiance.shape != ambient.shape or irradiance.shape != wind_speed.shape:
        raise ValueError(
            "Irradiance, ambient temperature, and wind speed must have the same shape."
        )
    if u0_wm2k <= 0.0 or u1_wm2k_per_mps < 0.0:
        raise ValueError("Faiman U0 must be positive and U1 must not be negative.")

    heat_loss_factor = float(u0_wm2k) + float(u1_wm2k_per_mps) * wind_speed
    return ambient + np.divide(
        irradiance,
        heat_loss_factor,
        out=np.zeros_like(irradiance),
        where=heat_loss_factor > 0.0,
    )


def temperature_adjusted_efficiency(
    cell_temperature_c: np.ndarray,
    efficiency_25: float,
    temperature_coefficient_per_k: float,
) -> np.ndarray:
    """Calculate module efficiency based on its value at 25 °C."""
    efficiency = float(efficiency_25) * (
        1.0
        + float(temperature_coefficient_per_k)
        * (np.asarray(cell_temperature_c, dtype=float) - 25.0)
    )
    return np.clip(efficiency, 0.0, 1.0)
