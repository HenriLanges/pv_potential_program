"""Iterative search for high-yield module tilt and orientation."""

from __future__ import annotations

import numpy as np
import pandas as pd

from .energy_production import annual_energy_per_m2_for_angles


def _angle_values(
    center: float,
    half_width: float,
    step: float,
    minimum: float,
    maximum: float,
) -> np.ndarray:
    start = max(minimum, center - half_width)
    stop = min(maximum, center + half_width)
    values = np.arange(start, stop + step * 0.5, step)
    return np.unique(np.clip(values, minimum, maximum))


def optimize_module_angles(
    horizontal_data: pd.DataFrame,
    efficiency_25: float,
    temperature_coefficient_per_k: float,
    faiman_u0_wm2k: float,
    faiman_u1_wm2k_per_mps: float,
    optical_reflection_loss: float,
    other_system_loss: float,
    ground_albedo: float = 0.2,
) -> dict[str, float | int]:
    """Optimize angles locally without additional PVGIS requests.

    First perform a coarse global search, then refine the best region twice.
    The objective is annual electrical yield per square metre, not self-consumption
    or monetary value.
    """
    cache: dict[tuple[float, float], float] = {}

    def evaluate(tilt_value: float, azimuth_value: float) -> float:
        tilt_value = float(np.clip(tilt_value, 0.0, 90.0))
        azimuth_value = float(azimuth_value % 360.0)
        key = (round(tilt_value, 4), round(azimuth_value, 4))
        if key not in cache:
            cache[key] = annual_energy_per_m2_for_angles(
                horizontal_data=horizontal_data,
                tilt_deg=tilt_value,
                azimuth_deg=azimuth_value,
                efficiency_25=efficiency_25,
                temperature_coefficient_per_k=temperature_coefficient_per_k,
                faiman_u0_wm2k=faiman_u0_wm2k,
                faiman_u1_wm2k_per_mps=faiman_u1_wm2k_per_mps,
                optical_reflection_loss=optical_reflection_loss,
                other_system_loss=other_system_loss,
                ground_albedo=ground_albedo,
            )
        return cache[key]

    def best_from_grid(
        tilts: np.ndarray,
        azimuths: np.ndarray,
    ) -> tuple[float, float, float]:
        candidates: list[tuple[float, float, float]] = []
        for candidate_tilt in tilts:
            for candidate_azimuth in azimuths:
                candidates.append(
                    (
                        evaluate(float(candidate_tilt), float(candidate_azimuth)),
                        float(candidate_tilt),
                        float(candidate_azimuth),
                    )
                )
        return max(candidates, key=lambda item: item[0])

    coarse_tilts = np.arange(0.0, 90.0 + 0.1, 10.0)
    coarse_azimuths = np.arange(0.0, 360.0, 20.0)
    best_yield, best_tilt, best_azimuth = best_from_grid(
        coarse_tilts, coarse_azimuths
    )

    medium_tilts = _angle_values(best_tilt, 10.0, 2.0, 0.0, 90.0)
    medium_azimuths = (
        np.arange(best_azimuth - 20.0, best_azimuth + 20.0 + 0.1, 5.0)
        % 360.0
    )
    best_yield, best_tilt, best_azimuth = best_from_grid(
        medium_tilts, np.unique(medium_azimuths)
    )

    fine_tilts = _angle_values(best_tilt, 2.0, 1.0, 0.0, 90.0)
    fine_azimuths = (
        np.arange(best_azimuth - 5.0, best_azimuth + 5.0 + 0.1, 1.0)
        % 360.0
    )
    best_yield, best_tilt, best_azimuth = best_from_grid(
        fine_tilts, np.unique(fine_azimuths)
    )

    if best_tilt < 0.5:
        best_azimuth = 180.0

    return {
        "tilt_deg": float(best_tilt),
        "azimuth_deg": float(best_azimuth % 360.0),
        "annual_energy_kwh_per_m2": float(best_yield),
        "evaluated_candidates": int(len(cache)),
    }
