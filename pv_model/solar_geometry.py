"""Solar position and conversion between azimuth conventions."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pvlib


def compass_to_pvgis_aspect(azimuth_deg: float) -> float:
    """Convert 0°=North/90°=East to the PVGIS convention."""
    aspect = (float(azimuth_deg) - 180.0) % 360.0
    if aspect > 180.0:
        aspect -= 360.0
    return aspect


def compass_direction(azimuth_deg: float) -> str:
    """Return the compass direction corresponding to an azimuth."""
    directions = [
        "North",
        "Northeast",
        "East",
        "Southeast",
        "South",
        "Southwest",
        "West",
        "Northwest",
    ]
    index = int(((float(azimuth_deg) % 360.0) + 22.5) // 45.0) % 8
    return directions[index]


def solar_geometry(
    time_utc: pd.Series | pd.DatetimeIndex,
    latitude: float,
    longitude: float,
) -> pd.DataFrame:
    """Calculate solar position with pvlib.

    The provided timestamps are interpreted as UTC.
    """
    index = pd.DatetimeIndex(time_utc)

    if index.tz is None:
        index = index.tz_localize("UTC")
    else:
        index = index.tz_convert("UTC")

    # Solar position using pvlib / NREL SPA
    solar_position = pvlib.solarposition.get_solarposition(
        time=index,
        latitude=float(latitude),
        longitude=float(longitude),
        method="nrel_numpy",
    )

    # Preserve the same outputs as before
    zenith_deg = solar_position["zenith"].to_numpy(dtype=float)
    solar_azimuth_deg = solar_position["azimuth"].to_numpy(dtype=float)

    # cos(zenith), clipped to 0 at night
    cos_zenith = np.maximum(
        np.cos(np.radians(zenith_deg)),
        0.0,
    )

    # Extraterrestrial direct normal irradiance using pvlib
    dni_extra = pvlib.irradiance.get_extra_radiation(
        index,
        method="spencer",
    ).to_numpy(dtype=float)

    return pd.DataFrame(
        {
            "solar_zenith_deg": zenith_deg,
            "solar_azimuth_deg": solar_azimuth_deg,
            "cos_zenith": cos_zenith,
            "dni_extra_wm2": dni_extra,
        },
        index=np.arange(len(index)),
    )