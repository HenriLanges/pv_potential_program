"""Electrical PV energy production from irradiance and Faiman temperature."""

from __future__ import annotations

import numpy as np
import pandas as pd

from .radiation import plane_irradiance_components
from .temperature_model import calculate_cell_temperature, temperature_adjusted_efficiency


def electrical_energy_kwh(
    irradiance_wm2: np.ndarray,
    ambient_temperature_c: np.ndarray,
    wind_speed_mps: np.ndarray,
    area_m2: float,
    efficiency_25: float,
    temperature_coefficient_per_k: float,
    faiman_u0_wm2k: float,
    faiman_u1_wm2k_per_mps: float,
    optical_reflection_loss: float,
    other_system_loss: float,
) -> np.ndarray:
    """Calculate electrical energy per hourly time step in kWh."""
    irradiance = np.maximum(np.asarray(irradiance_wm2, dtype=float), 0.0)
    cell_temperature = calculate_cell_temperature(
        irradiance_wm2=irradiance,
        ambient_temperature_c=ambient_temperature_c,
        wind_speed_mps=wind_speed_mps,
        u0_wm2k=faiman_u0_wm2k,
        u1_wm2k_per_mps=faiman_u1_wm2k_per_mps,
    )
    efficiency = temperature_adjusted_efficiency(
        cell_temperature_c=cell_temperature,
        efficiency_25=efficiency_25,
        temperature_coefficient_per_k=temperature_coefficient_per_k,
    )
    optical_factor = 1.0 - float(np.clip(optical_reflection_loss, 0.0, 1.0))
    system_factor = 1.0 - float(np.clip(other_system_loss, 0.0, 1.0))
    return irradiance * float(area_m2) * efficiency * optical_factor * system_factor / 1000.0


def pv_energy_for_area(
    average_year: pd.DataFrame,
    area_m2: float,
    efficiency_25: float,
    temperature_coefficient_per_k: float,
    faiman_u0_wm2k: float,
    faiman_u1_wm2k_per_mps: float,
    optical_reflection_loss: float = 0.0,
    other_system_loss: float = 0.0,
) -> pd.Series:
    """Calculate hourly electrical PV energy in kWh."""
    required = {"irradiance_poa_wm2", "ambient_temperature_c", "wind_speed_mps"}
    missing = required.difference(average_year.columns)
    if missing:
        raise ValueError("Columns required by the Faiman model are missing: " + ", ".join(sorted(missing)))
    energy = electrical_energy_kwh(
        irradiance_wm2=average_year["irradiance_poa_wm2"].to_numpy(dtype=float),
        ambient_temperature_c=average_year["ambient_temperature_c"].to_numpy(dtype=float),
        wind_speed_mps=average_year["wind_speed_mps"].to_numpy(dtype=float),
        area_m2=area_m2,
        efficiency_25=efficiency_25,
        temperature_coefficient_per_k=temperature_coefficient_per_k,
        faiman_u0_wm2k=faiman_u0_wm2k,
        faiman_u1_wm2k_per_mps=faiman_u1_wm2k_per_mps,
        optical_reflection_loss=optical_reflection_loss,
        other_system_loss=other_system_loss,
    )
    return pd.Series(energy, index=average_year.index, name="pv_generation_kwh")


def annual_energy_per_m2_for_angles(
    horizontal_data: pd.DataFrame,
    tilt_deg: float,
    azimuth_deg: float,
    efficiency_25: float,
    temperature_coefficient_per_k: float,
    faiman_u0_wm2k: float,
    faiman_u1_wm2k_per_mps: float,
    optical_reflection_loss: float,
    other_system_loss: float,
    ground_albedo: float = 0.2,
) -> float:
    """Calculate mean annual yield per m² for an angle combination."""
    poa, _, _, _ = plane_irradiance_components(
        horizontal_data, tilt_deg=tilt_deg, azimuth_deg=azimuth_deg, ground_albedo=ground_albedo
    )
    energy = electrical_energy_kwh(
        irradiance_wm2=poa,
        ambient_temperature_c=horizontal_data["ambient_temperature_c"].to_numpy(dtype=float),
        wind_speed_mps=horizontal_data["wind_speed_mps"].to_numpy(dtype=float),
        area_m2=1.0,
        efficiency_25=efficiency_25,
        temperature_coefficient_per_k=temperature_coefficient_per_k,
        faiman_u0_wm2k=faiman_u0_wm2k,
        faiman_u1_wm2k_per_mps=faiman_u1_wm2k_per_mps,
        optical_reflection_loss=optical_reflection_loss,
        other_system_loss=other_system_loss,
    )
    time_utc = pd.DatetimeIndex(horizontal_data["time_utc"])
    non_leap_mask = ~((time_utc.month == 2) & (time_utc.day == 29))
    years = len(np.unique(time_utc.year))
    if years == 0:
        raise ValueError("The weather data do not contain a usable year.")
    return float(energy[non_leap_mask].sum() / years)
