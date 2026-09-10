"""Reproducible 100-case comparison between the local PV model and PVGIS 5.3.

The local model uses one horizontal PVGIS weather request per location and performs
its own irradiance transposition, Faiman temperature calculation and electrical
conversion.  Each benchmark case then uses one independent tilted PVGIS request
with ``pvcalculation=1``.  That single reference request returns both the tilted
irradiance components and PV power, enabling radiation and energy validation with
identical location, years, tilt, azimuth and nominal peak power.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
import time
from typing import Callable

import numpy as np
import pandas as pd

from .api_request import PVGISRequestError, fetch_pvgis_horizontal
from .energy_production import pv_energy_for_area
from .pvgis_validation import fetch_pvgis_pv_output
from .radiation import weather_for_angles
from .validation_statistics import error_driver_statistics, regression_statistics


@dataclass(frozen=True)
class BenchmarkCase:
    case_id: int
    location: str
    latitude: float
    longitude: float
    tilt_deg: float
    azimuth_deg: float
    peak_power_kwp: float


LOCATIONS = [
    ("Berlin", 52.5200, 13.4050),
    ("Hamburg", 53.5511, 9.9937),
    ("Munich", 48.1351, 11.5820),
    ("Cologne", 50.9375, 6.9603),
    ("Frankfurt", 50.1109, 8.6821),
    ("Stuttgart", 48.7758, 9.1829),
    ("Leipzig", 51.3397, 12.3731),
    ("Dresden", 51.0504, 13.7373),
    ("Bremen", 53.0793, 8.8017),
    ("Nuremberg", 49.4521, 11.0767),
]

CONFIGURATIONS = [
    (0.0, 180.0, 3.0),
    (15.0, 180.0, 5.0),
    (30.0, 180.0, 10.0),
    (45.0, 180.0, 20.0),
    (60.0, 180.0, 50.0),
    (30.0, 90.0, 7.5),
    (30.0, 135.0, 12.5),
    (30.0, 225.0, 30.0),
    (30.0, 270.0, 75.0),
    (45.0, 135.0, 100.0),
]


def default_100_cases() -> pd.DataFrame:
    """Return the fixed 10-location x 10-configuration benchmark matrix."""
    rows = []
    case_id = 1
    for location, lat, lon in LOCATIONS:
        for tilt, azimuth, kwp in CONFIGURATIONS:
            rows.append(asdict(BenchmarkCase(case_id, location, lat, lon, tilt, azimuth, kwp)))
            case_id += 1
    return pd.DataFrame(rows)


def validate_case_table(cases: pd.DataFrame, require_100: bool = True) -> pd.DataFrame:
    required = ["case_id", "location", "latitude", "longitude", "tilt_deg", "azimuth_deg", "peak_power_kwp"]
    missing = [c for c in required if c not in cases.columns]
    if missing:
        raise ValueError("Case table is missing columns: " + ", ".join(missing))
    out = cases[required].copy()
    if require_100 and len(out) != 100:
        raise ValueError(f"Exactly 100 cases are required; received {len(out)}.")
    for c in ["latitude", "longitude", "tilt_deg", "azimuth_deg", "peak_power_kwp"]:
        out[c] = pd.to_numeric(out[c], errors="raise")
    if not out["case_id"].is_unique:
        raise ValueError("case_id values must be unique.")
    if not out["latitude"].between(-90, 90).all():
        raise ValueError("Latitude must be between -90 and 90 degrees.")
    if not out["longitude"].between(-180, 180).all():
        raise ValueError("Longitude must be between -180 and 180 degrees.")
    if not out["tilt_deg"].between(0, 90).all():
        raise ValueError("Tilt must be between 0 and 90 degrees.")
    if not out["azimuth_deg"].between(0, 360).all():
        raise ValueError("Azimuth must be between 0 and 360 degrees.")
    if not (out["peak_power_kwp"] > 0).all():
        raise ValueError("Peak power must be positive.")
    return out.reset_index(drop=True)


def _mean_annual_sum(values, time_utc) -> float:
    idx = pd.DatetimeIndex(time_utc)
    values = np.asarray(values, dtype=float)
    mask = ~((idx.month == 2) & (idx.day == 29))
    years = np.unique(idx[mask].year)
    if len(years) == 0:
        raise ValueError("No usable year in time series.")
    return float(values[mask].sum() / len(years))


def _retry_call(func, *args, retries: int = 4, **kwargs):
    last = None
    for attempt in range(retries):
        try:
            return func(*args, **kwargs)
        except PVGISRequestError as exc:
            last = exc
            if attempt == retries - 1:
                raise
            time.sleep(0.75 * (attempt + 1))
    raise last  # pragma: no cover


def _case_result(
    case: pd.Series,
    horizontal: pd.DataFrame,
    start_year: int,
    end_year: int,
    efficiency_25: float,
    temperature_coefficient_per_k: float,
    faiman_u0_wm2k: float,
    faiman_u1_wm2k_per_mps: float,
    ground_albedo: float,
    system_loss_pct: float,
    optical_reflection_loss_pct: float,
    timezone: str,
) -> dict:
    tilt = float(case.tilt_deg)
    azimuth = float(case.azimuth_deg)
    peak_kwp = float(case.peak_power_kwp)

    tilted = weather_for_angles(horizontal, tilt, azimuth, ground_albedo=ground_albedo)
    area_m2 = peak_kwp / efficiency_25
    model_hourly_kwh = pv_energy_for_area(
        tilted,
        area_m2=area_m2,
        efficiency_25=efficiency_25,
        temperature_coefficient_per_k=temperature_coefficient_per_k,
        faiman_u0_wm2k=faiman_u0_wm2k,
        faiman_u1_wm2k_per_mps=faiman_u1_wm2k_per_mps,
        optical_reflection_loss=optical_reflection_loss_pct / 100.0,
        other_system_loss=system_loss_pct / 100.0,
    )

    reference = _retry_call(
        fetch_pvgis_pv_output,
        latitude=float(case.latitude),
        longitude=float(case.longitude),
        tilt_deg=tilt,
        azimuth_deg=azimuth,
        peak_power_kwp=peak_kwp,
        system_loss_pct=system_loss_pct,
        start_year=start_year,
        end_year=end_year,
        timezone=timezone,
    )

    model_energy = _mean_annual_sum(model_hourly_kwh.to_numpy(), tilted["time_utc"])
    pvgis_energy = _mean_annual_sum(reference["pvgis_power_w"].to_numpy(), reference["time_utc"]) / 1000.0

    model_direct = _mean_annual_sum(tilted["beam_wm2"], tilted["time_utc"]) / 1000.0
    model_diffuse = _mean_annual_sum(tilted["diffuse_wm2"], tilted["time_utc"]) / 1000.0
    model_reflected = _mean_annual_sum(tilted["ground_reflected_wm2"], tilted["time_utc"]) / 1000.0
    model_global = _mean_annual_sum(tilted["irradiance_poa_wm2"], tilted["time_utc"]) / 1000.0

    pvgis_direct = _mean_annual_sum(reference["pvgis_beam_poa_wm2"], reference["time_utc"]) / 1000.0
    pvgis_diffuse = _mean_annual_sum(reference["pvgis_diffuse_poa_wm2"], reference["time_utc"]) / 1000.0
    pvgis_reflected = _mean_annual_sum(reference["pvgis_reflected_poa_wm2"], reference["time_utc"]) / 1000.0
    pvgis_global = _mean_annual_sum(reference["pvgis_global_poa_wm2"], reference["time_utc"]) / 1000.0

    def errors(model, ref, prefix):
        diff = model - ref
        pct = 100.0 * diff / ref if ref else np.nan
        return {f"{prefix}_error": diff, f"{prefix}_error_pct": pct, f"{prefix}_abs_error_pct": abs(pct) if np.isfinite(pct) else np.nan}

    result = {
        **case.to_dict(),
        "area_m2": area_m2,
        "azimuth_deviation_south_deg": abs(((azimuth - 180.0 + 180.0) % 360.0) - 180.0),
        "model_energy_kwh_a": model_energy,
        "pvgis_energy_kwh_a": pvgis_energy,
        "model_specific_yield_kwh_kwp_a": model_energy / peak_kwp,
        "pvgis_specific_yield_kwh_kwp_a": pvgis_energy / peak_kwp,
        "model_direct_poa_kwh_m2_a": model_direct,
        "pvgis_direct_poa_kwh_m2_a": pvgis_direct,
        "model_diffuse_poa_kwh_m2_a": model_diffuse,
        "pvgis_diffuse_poa_kwh_m2_a": pvgis_diffuse,
        "model_reflected_poa_kwh_m2_a": model_reflected,
        "pvgis_reflected_poa_kwh_m2_a": pvgis_reflected,
        "model_global_poa_kwh_m2_a": model_global,
        "pvgis_global_poa_kwh_m2_a": pvgis_global,
    }
    result.update(errors(model_energy, pvgis_energy, "energy"))
    result.update(errors(model_direct, pvgis_direct, "direct_poa"))
    result.update(errors(model_diffuse, pvgis_diffuse, "diffuse_poa"))
    result.update(errors(model_reflected, pvgis_reflected, "reflected_poa"))
    result.update(errors(model_global, pvgis_global, "global_poa"))
    return result


def run_100_case_validation(
    cases: pd.DataFrame | None = None,
    start_year: int = 2014,
    end_year: int = 2023,
    efficiency_25: float = 0.20,
    temperature_coefficient_per_k: float = -0.004,
    faiman_u0_wm2k: float = 25.0,
    faiman_u1_wm2k_per_mps: float = 6.84,
    ground_albedo: float = 0.20,
    system_loss_pct: float = 14.0,
    optical_reflection_loss_pct: float = 0.0,
    timezone: str = "Europe/Berlin",
    progress_callback: Callable[[int, int, str], None] | None = None,
) -> tuple[pd.DataFrame, dict[str, dict[str, float]], pd.DataFrame]:
    """Run exactly 100 reproducible cases and return cases, statistics and drivers."""
    cases = validate_case_table(default_100_cases() if cases is None else cases, require_100=True)
    if start_year > end_year:
        raise ValueError("start_year must not exceed end_year.")
    if start_year < 2005 or end_year > 2023:
        raise ValueError("PVGIS 5.3 benchmark years must be within 2005–2023.")
    if not (0 < efficiency_25 <= 1):
        raise ValueError("efficiency_25 must be in (0, 1].")

    horizontal_cache: dict[tuple[float, float], pd.DataFrame] = {}
    records = []
    total = len(cases)
    for i, case in cases.iterrows():
        key = (float(case.latitude), float(case.longitude))
        if key not in horizontal_cache:
            if progress_callback:
                progress_callback(i, total, f"Loading horizontal PVGIS weather for {case.location}")
            horizontal_cache[key] = _retry_call(
                fetch_pvgis_horizontal,
                latitude=key[0], longitude=key[1], start_year=start_year, end_year=end_year, timezone=timezone,
            )
        if progress_callback:
            progress_callback(i, total, f"Case {int(case.case_id)}/100: {case.location}, {case.tilt_deg:g}°, {case.azimuth_deg:g}°, {case.peak_power_kwp:g} kWp")
        records.append(_case_result(
            case, horizontal_cache[key], start_year, end_year, efficiency_25,
            temperature_coefficient_per_k, faiman_u0_wm2k, faiman_u1_wm2k_per_mps,
            ground_albedo, system_loss_pct, optical_reflection_loss_pct, timezone,
        ))
        if progress_callback:
            progress_callback(i + 1, total, f"Completed {i + 1}/100 cases")

    results = pd.DataFrame(records)
    stats = {
        "energy": regression_statistics(results["pvgis_energy_kwh_a"], results["model_energy_kwh_a"]),
        "specific_yield": regression_statistics(results["pvgis_specific_yield_kwh_kwp_a"], results["model_specific_yield_kwh_kwp_a"]),
        "direct_poa": regression_statistics(results["pvgis_direct_poa_kwh_m2_a"], results["model_direct_poa_kwh_m2_a"]),
        "global_poa": regression_statistics(results["pvgis_global_poa_kwh_m2_a"], results["model_global_poa_kwh_m2_a"]),
    }
    drivers = error_driver_statistics(
        results,
        "energy_error_pct",
        ["latitude", "longitude", "tilt_deg", "azimuth_deviation_south_deg", "peak_power_kwp"],
    )
    return results, stats, drivers
