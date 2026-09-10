"""Independent PVGIS reference requests for validating irradiance and PV yield.

The main model deliberately starts from one horizontal PVGIS request and performs
its own transposition and electrical calculation locally.  This module makes two
additional, independent PVGIS ``seriescalc`` requests so those local results can
be checked against PVGIS itself:

1. tilted-plane radiation for the entered module slope and azimuth;
2. tilted-plane PV output for the same orientation plus a nominal peak power.

Azimuth in the user interface follows the compass convention
0°=North, 90°=East, 180°=South, 270°=West. PVGIS uses 0°=South,
+90°=West and -90°=East, so the existing conversion helper is used here.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import requests

from .api_request import PVGISRequestError
from .constants import END_YEAR, PVGIS_URL, START_YEAR
from .solar_geometry import compass_to_pvgis_aspect
from .time_series import utc_to_local_hour


def _request_seriescalc(params: dict) -> dict:
    """Send a PVGIS seriescalc request and return the decoded JSON payload."""
    try:
        response = requests.get(PVGIS_URL, params=params, timeout=(20, 180))
        response.raise_for_status()
    except requests.Timeout as exc:
        raise PVGISRequestError(
            "The PVGIS validation request timed out. Please try again later "
            "or check the network/firewall."
        ) from exc
    except requests.RequestException as exc:
        raise PVGISRequestError(
            "PVGIS validation could not be reached. Please check the internet "
            "connection, proxy, or firewall."
        ) from exc

    try:
        payload = response.json()
    except ValueError as exc:
        raise PVGISRequestError("PVGIS returned an invalid JSON response.") from exc

    if not isinstance(payload, dict):
        raise PVGISRequestError("PVGIS returned an unexpected response format.")
    return payload


def _parse_hourly_payload(payload: dict, timezone: str, require_power: bool) -> pd.DataFrame:
    """Parse tilted-plane hourly radiation and, optionally, PV power."""
    try:
        hourly = payload["outputs"]["hourly"]
    except (KeyError, TypeError) as exc:
        message = payload.get("message", "Unexpected PVGIS validation response")
        raise ValueError(message) from exc

    frame = pd.DataFrame(hourly)
    if frame.empty:
        raise ValueError("PVGIS returned no hourly validation values.")

    required = {"time", "Gb(i)", "Gd(i)", "Gr(i)"}
    if require_power:
        required.add("P")
    missing = required.difference(frame.columns)
    if missing:
        raise ValueError(
            "The PVGIS validation response is missing: " + ", ".join(sorted(missing))
        )

    frame["time_utc"] = pd.to_datetime(
        frame["time"], format="%Y%m%d:%H%M", errors="raise"
    ).dt.tz_localize("UTC")
    frame["time_local"] = utc_to_local_hour(frame["time_utc"], timezone)

    frame["pvgis_beam_poa_wm2"] = pd.to_numeric(frame["Gb(i)"], errors="coerce")
    frame["pvgis_diffuse_poa_wm2"] = pd.to_numeric(frame["Gd(i)"], errors="coerce")
    frame["pvgis_reflected_poa_wm2"] = pd.to_numeric(frame["Gr(i)"], errors="coerce")
    frame["pvgis_global_poa_wm2"] = (
        frame["pvgis_beam_poa_wm2"]
        + frame["pvgis_diffuse_poa_wm2"]
        + frame["pvgis_reflected_poa_wm2"]
    ).clip(lower=0.0)

    columns = [
        "time_utc",
        "time_local",
        "pvgis_beam_poa_wm2",
        "pvgis_diffuse_poa_wm2",
        "pvgis_reflected_poa_wm2",
        "pvgis_global_poa_wm2",
    ]

    if require_power:
        frame["pvgis_power_w"] = pd.to_numeric(frame["P"], errors="coerce").clip(lower=0.0)
        columns.append("pvgis_power_w")

    if frame[columns[2:]].isna().any().any():
        raise ValueError("PVGIS returned non-numeric radiation or PV-power values.")

    return frame[columns].copy()


def fetch_pvgis_tilted_radiation(
    latitude: float,
    longitude: float,
    tilt_deg: float,
    azimuth_deg: float,
    start_year: int = START_YEAR,
    end_year: int = END_YEAR,
    timezone: str = "Europe/Berlin",
) -> pd.DataFrame:
    """Request PVGIS radiation components directly on the entered module plane."""
    params = {
        "lat": float(latitude),
        "lon": float(longitude),
        "startyear": int(start_year),
        "endyear": int(end_year),
        "pvcalculation": 0,
        "angle": float(tilt_deg),
        "aspect": compass_to_pvgis_aspect(azimuth_deg),
        "components": 1,
        "usehorizon": 1,
        "outputformat": "json",
    }
    payload = _request_seriescalc(params)
    return _parse_hourly_payload(payload, timezone=timezone, require_power=False)


def fetch_pvgis_pv_output(
    latitude: float,
    longitude: float,
    tilt_deg: float,
    azimuth_deg: float,
    peak_power_kwp: float,
    system_loss_pct: float,
    start_year: int = START_YEAR,
    end_year: int = END_YEAR,
    timezone: str = "Europe/Berlin",
    pv_technology: str = "crystSi",
    mounting_place: str = "free",
) -> pd.DataFrame:
    """Request hourly PVGIS PV power for the same orientation and actual kWp."""
    if peak_power_kwp <= 0.0:
        raise ValueError("PV peak power must be greater than zero for PVGIS validation.")

    params = {
        "lat": float(latitude),
        "lon": float(longitude),
        "startyear": int(start_year),
        "endyear": int(end_year),
        "pvcalculation": 1,
        "peakpower": float(peak_power_kwp),
        "loss": float(np.clip(system_loss_pct, 0.0, 100.0)),
        "pvtechchoice": pv_technology,
        "mountingplace": mounting_place,
        "angle": float(tilt_deg),
        "aspect": compass_to_pvgis_aspect(azimuth_deg),
        "components": 1,
        "usehorizon": 1,
        "outputformat": "json",
    }
    payload = _request_seriescalc(params)
    return _parse_hourly_payload(payload, timezone=timezone, require_power=True)


def _non_leap_mask(time_utc: pd.Series | pd.DatetimeIndex) -> np.ndarray:
    index = pd.DatetimeIndex(time_utc)
    return ~((index.month == 2) & (index.day == 29))


def _mean_annual_sum(values: np.ndarray, time_utc: pd.Series | pd.DatetimeIndex) -> float:
    """Mean annual sum for hourly values, excluding 29 February."""
    index = pd.DatetimeIndex(time_utc)
    mask = _non_leap_mask(index)
    years = np.unique(index[mask].year)
    if len(years) == 0:
        raise ValueError("Validation data do not contain a usable year.")
    return float(np.asarray(values, dtype=float)[mask].sum() / len(years))


def radiation_comparison_summary(
    program_tilted: pd.DataFrame,
    pvgis_tilted: pd.DataFrame,
) -> pd.DataFrame:
    """Compare mean annual in-plane irradiation from the program and PVGIS."""
    program_metrics = {
        "Direct irradiation": "beam_wm2",
        "Diffuse irradiation": "diffuse_wm2",
        "Ground-reflected irradiation": "ground_reflected_wm2",
        "Global POA irradiation": "irradiance_poa_wm2",
    }
    pvgis_metrics = {
        "Direct irradiation": "pvgis_beam_poa_wm2",
        "Diffuse irradiation": "pvgis_diffuse_poa_wm2",
        "Ground-reflected irradiation": "pvgis_reflected_poa_wm2",
        "Global POA irradiation": "pvgis_global_poa_wm2",
    }

    records: list[dict[str, float | str]] = []
    for label, program_column in program_metrics.items():
        pvgis_column = pvgis_metrics[label]
        program_value = _mean_annual_sum(
            program_tilted[program_column].to_numpy(dtype=float),
            program_tilted["time_utc"],
        ) / 1000.0
        pvgis_value = _mean_annual_sum(
            pvgis_tilted[pvgis_column].to_numpy(dtype=float),
            pvgis_tilted["time_utc"],
        ) / 1000.0
        difference = program_value - pvgis_value
        difference_pct = 100.0 * difference / pvgis_value if pvgis_value else np.nan
        records.append(
            {
                "Metric": label,
                "Program_kWh_m2_a": program_value,
                "PVGIS_kWh_m2_a": pvgis_value,
                "Difference_kWh_m2_a": difference,
                "Difference_pct": difference_pct,
            }
        )
    return pd.DataFrame(records)


def pvgis_mean_annual_energy_kwh(pvgis_pv_output: pd.DataFrame) -> float:
    """Convert hourly PVGIS power [W] to mean annual electrical energy [kWh/a]."""
    # Each seriescalc value is an hourly average power. Multiplication by one hour
    # and division by 1000 therefore yields kWh for that time step.
    return _mean_annual_sum(
        pvgis_pv_output["pvgis_power_w"].to_numpy(dtype=float),
        pvgis_pv_output["time_utc"],
    ) / 1000.0


def energy_comparison_summary(
    program_energy_kwh_a: float,
    pvgis_pv_output: pd.DataFrame,
    peak_power_kwp: float,
) -> dict[str, float]:
    """Compare program PV generation with the independent PVGIS PV calculation."""
    pvgis_energy = pvgis_mean_annual_energy_kwh(pvgis_pv_output)
    difference = float(program_energy_kwh_a) - pvgis_energy
    difference_pct = 100.0 * difference / pvgis_energy if pvgis_energy else np.nan
    return {
        "peak_power_kwp": float(peak_power_kwp),
        "program_energy_kwh_a": float(program_energy_kwh_a),
        "pvgis_energy_kwh_a": pvgis_energy,
        "difference_kwh_a": difference,
        "difference_pct": difference_pct,
        "pvgis_specific_yield_kwh_per_kwp_a": (
            pvgis_energy / float(peak_power_kwp) if peak_power_kwp else np.nan
        ),
    }


def add_pvgis_scaled_generation_columns(
    results: pd.DataFrame,
    specific_yield_kwh_per_kwp_a: float,
) -> pd.DataFrame:
    """Add PVGIS-reference generation to each PV-area row using specific yield."""
    output = results.copy()
    output["PVGIS_Generation_kWh_a"] = (
        output["PV_Capacity_kWp"].astype(float) * float(specific_yield_kwh_per_kwp_a)
    )
    output["Generation_Difference_vs_PVGIS_kWh_a"] = (
        output["Electricity_Generation_kWh_a"] - output["PVGIS_Generation_kWh_a"]
    )
    denominator = output["PVGIS_Generation_kWh_a"].replace(0.0, np.nan)
    output["Generation_Difference_vs_PVGIS_pct"] = (
        100.0 * output["Generation_Difference_vs_PVGIS_kWh_a"] / denominator
    )
    return output
