"""Convert horizontal irradiance to the tilted module plane."""

from __future__ import annotations

import numpy as np
import pandas as pd


def plane_irradiance_components(
    horizontal_data: pd.DataFrame,
    tilt_deg: float,
    azimuth_deg: float,
    ground_albedo: float = 0.2,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Calculate direct, diffuse, and ground-reflected module irradiance.

    A simple isotropic diffuse irradiance model is used. Azimuth follows
    0°=North, 90°=East, 180°=South, 270°=West.
    """
    tilt = np.radians(float(np.clip(tilt_deg, 0.0, 90.0)))
    surface_azimuth = np.radians(float(azimuth_deg) % 360.0)
    solar_zenith = np.radians(
        horizontal_data["solar_zenith_deg"].to_numpy(dtype=float)
    )
    solar_azimuth = np.radians(
        horizontal_data["solar_azimuth_deg"].to_numpy(dtype=float)
    )

    cos_aoi = (
        np.cos(solar_zenith) * np.cos(tilt)
        + np.sin(solar_zenith)
        * np.sin(tilt)
        * np.cos(solar_azimuth - surface_azimuth)
    )
    cos_aoi = np.maximum(cos_aoi, 0.0)

    dni = horizontal_data["dni_wm2"].to_numpy(dtype=float)
    dhi = horizontal_data["diffuse_horizontal_wm2"].to_numpy(dtype=float)
    ghi = horizontal_data["global_horizontal_wm2"].to_numpy(dtype=float)

    poa_direct = dni * cos_aoi
    poa_sky_diffuse = dhi * (1.0 + np.cos(tilt)) / 2.0
    poa_ground = (
        ghi
        * float(np.clip(ground_albedo, 0.0, 1.0))
        * (1.0 - np.cos(tilt))
        / 2.0
    )
    poa_global = np.maximum(poa_direct + poa_sky_diffuse + poa_ground, 0.0)
    return poa_global, poa_direct, poa_sky_diffuse, poa_ground


def weather_for_angles(
    horizontal_data: pd.DataFrame,
    tilt_deg: float,
    azimuth_deg: float,
    ground_albedo: float = 0.2,
) -> pd.DataFrame:
    """Create weather values for module angles from horizontal input data."""
    poa, beam, diffuse, reflected = plane_irradiance_components(
        horizontal_data,
        tilt_deg=tilt_deg,
        azimuth_deg=azimuth_deg,
        ground_albedo=ground_albedo,
    )
    result = horizontal_data[
        ["time_utc", "time_local", "ambient_temperature_c", "wind_speed_mps"]
    ].copy()
    result["irradiance_poa_wm2"] = poa
    result["beam_wm2"] = beam
    result["diffuse_wm2"] = diffuse
    result["ground_reflected_wm2"] = reflected
    return result
