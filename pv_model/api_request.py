"""PVGIS HTTP request and preparation of horizontal weather data."""

from __future__ import annotations

import numpy as np
import pandas as pd
import requests

from .constants import END_YEAR, PVGIS_URL, START_YEAR
from .radiation import weather_for_angles
from .solar_geometry import solar_geometry
from .time_series import utc_to_local_hour


class PVGISRequestError(RuntimeError):
    """Readable error for failed PVGIS connections."""


def _parse_horizontal_response(
    payload: dict,
    latitude: float,
    longitude: float,
    timezone: str,
) -> pd.DataFrame:
    """Validate and convert the PVGIS JSON response."""
    try:
        hourly = payload["outputs"]["hourly"]
    except (KeyError, TypeError) as exc:
        message = payload.get("message", "Unexpected PVGIS response")
        raise ValueError(message) from exc

    frame = pd.DataFrame(hourly)
    if frame.empty:
        raise ValueError("PVGIS returned no hourly values.")

    required_columns = {"time", "Gb(i)", "Gd(i)", "T2m", "WS10m"}
    missing_columns = required_columns.difference(frame.columns)
    if missing_columns:
        missing_text = ", ".join(sorted(missing_columns))
        raise ValueError(f"The PVGIS response is missing: {missing_text}.")

    frame["time_utc"] = pd.to_datetime(
        frame["time"], format="%Y%m%d:%H%M", errors="raise"
    ).dt.tz_localize("UTC")
    frame["time_local"] = utc_to_local_hour(frame["time_utc"], timezone)

    frame["beam_horizontal_wm2"] = pd.to_numeric(frame["Gb(i)"], errors="coerce")
    frame["diffuse_horizontal_wm2"] = pd.to_numeric(
        frame["Gd(i)"], errors="coerce"
    )
    frame["global_horizontal_wm2"] = (
        frame["beam_horizontal_wm2"] + frame["diffuse_horizontal_wm2"]
    ).clip(lower=0.0)
    frame["ambient_temperature_c"] = pd.to_numeric(frame["T2m"], errors="coerce")
    frame["wind_speed_mps"] = pd.to_numeric(frame["WS10m"], errors="coerce").clip(lower=0.0)

    numeric_columns = [
        "beam_horizontal_wm2",
        "diffuse_horizontal_wm2",
        "global_horizontal_wm2",
        "ambient_temperature_c",
        "wind_speed_mps",
    ]
    if frame[numeric_columns].isna().any().any():
        raise ValueError("PVGIS contains invalid irradiance, temperature, or wind values.")

    geometry = solar_geometry(frame["time_utc"], latitude, longitude)
    for column in geometry.columns:
        frame[column] = geometry[column].to_numpy()

    cos_zenith = frame["cos_zenith"].to_numpy(dtype=float)
    beam_horizontal = frame["beam_horizontal_wm2"].to_numpy(dtype=float)
    dni_extra = frame["dni_extra_wm2"].to_numpy(dtype=float)
    dni = np.divide(
        beam_horizontal,
        cos_zenith,
        out=np.zeros_like(beam_horizontal),
        where=cos_zenith > 1e-3,
    )
    frame["dni_wm2"] = np.clip(dni, 0.0, dni_extra)

    columns = [
        "time_utc",
        "time_local",
        "beam_horizontal_wm2",
        "diffuse_horizontal_wm2",
        "global_horizontal_wm2",
        "ambient_temperature_c",
        "wind_speed_mps",
        "solar_zenith_deg",
        "solar_azimuth_deg",
        "cos_zenith",
        "dni_wm2",
    ]
    return frame[columns].copy()


def fetch_pvgis_horizontal(
    latitude: float,
    longitude: float,
    start_year: int = START_YEAR,
    end_year: int = END_YEAR,
    timezone: str = "Europe/Berlin",
) -> pd.DataFrame:
    """Query PVGIS exactly once for a horizontal plane."""
    params = {
        "lat": float(latitude),
        "lon": float(longitude),
        "startyear": int(start_year),
        "endyear": int(end_year),
        "pvcalculation": 0,
        "angle": 0.0,
        "aspect": 0.0,
        "components": 1,
        "usehorizon": 1,
        "outputformat": "json",
    }

    try:
        response = requests.get(PVGIS_URL, params=params, timeout=(20, 180))
        response.raise_for_status()
    except requests.Timeout as exc:
        raise PVGISRequestError(
            "The PVGIS connection timed out. Please try again later "
            "or check the network/firewall."
        ) from exc
    except requests.RequestException as exc:
        raise PVGISRequestError(
            "PVGIS could not be reached. Please check the internet connection, proxy, "
            "or firewall."
        ) from exc

    return _parse_horizontal_response(
        response.json(),
        latitude=latitude,
        longitude=longitude,
        timezone=timezone,
    )


def fetch_pvgis_hourly(
    latitude: float,
    longitude: float,
    tilt_deg: float,
    azimuth_deg: float,
    start_year: int = START_YEAR,
    end_year: int = END_YEAR,
    timezone: str = "Europe/Berlin",
    ground_albedo: float = 0.2,
) -> pd.DataFrame:
    """Compatibility function: one request followed by local angle conversion."""
    horizontal = fetch_pvgis_horizontal(
        latitude=latitude,
        longitude=longitude,
        start_year=start_year,
        end_year=end_year,
        timezone=timezone,
    )
    return weather_for_angles(
        horizontal,
        tilt_deg=tilt_deg,
        azimuth_deg=azimuth_deg,
        ground_albedo=ground_albedo,
    )
