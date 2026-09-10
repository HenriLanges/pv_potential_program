"""Area and battery simulation from the PV model, energy balance, and costs."""

from __future__ import annotations

import numpy as np
import pandas as pd

from .battery_model import simulate_battery_dispatch
from .economics import calculate_annual_economic_value
from .energy_production import pv_energy_for_area


def simulate_area_battery_range(
    average_year: pd.DataFrame,
    load_kwh: pd.Series,
    areas_m2: np.ndarray,
    battery_capacities_kwh: np.ndarray,
    efficiency_25: float,
    temperature_coefficient_per_k: float,
    faiman_u0_wm2k: float,
    faiman_u1_wm2k_per_mps: float,
    optical_reflection_loss: float,
    other_system_loss: float,
    battery_charge_efficiency: float = 0.95,
    battery_discharge_efficiency: float | None = None,
    electricity_price_eur_per_kwh: float = 0.0,
    feed_in_tariff_eur_per_kwh: float = 0.0,
) -> pd.DataFrame:
    """Calculate every combination of PV area and battery capacity."""
    if len(average_year) != len(load_kwh):
        raise ValueError("PV and load time series do not have the same length.")

    records: list[dict[str, float]] = []
    load_values = load_kwh.to_numpy(dtype=float)
    capacities = np.asarray(battery_capacities_kwh, dtype=float)
    if np.any(capacities < 0.0):
        raise ValueError("Battery capacities must not be negative.")

    for area in np.asarray(areas_m2, dtype=float):
        generation = pv_energy_for_area(
            average_year=average_year,
            area_m2=float(area),
            efficiency_25=efficiency_25,
            temperature_coefficient_per_k=temperature_coefficient_per_k,
            faiman_u0_wm2k=faiman_u0_wm2k,
            faiman_u1_wm2k_per_mps=faiman_u1_wm2k_per_mps,
            optical_reflection_loss=optical_reflection_loss,
            other_system_loss=other_system_loss,
        ).to_numpy(dtype=float)

        for capacity in capacities:
            balance = simulate_battery_dispatch(
                generation_kwh=generation,
                load_kwh=load_values,
                capacity_kwh=float(capacity),
                charge_efficiency=battery_charge_efficiency,
                discharge_efficiency=battery_discharge_efficiency,
            )
            economics = calculate_annual_economic_value(
                direct_use_kwh=float(balance["usable_energy_sum_kwh"]),
                feed_in_kwh=float(balance["feed_in_sum_kwh"]),
                electricity_price_eur_per_kwh=electricity_price_eur_per_kwh,
                feed_in_tariff_eur_per_kwh=feed_in_tariff_eur_per_kwh,
            )
            generation_sum = float(balance["generation_sum_kwh"])
            usable_sum = float(balance["usable_energy_sum_kwh"])
            annual_load = float(balance["annual_load_kwh"])
            records.append({
                "Area_m2": float(area),
                "Battery_kWh": float(capacity),
                "PV_Capacity_kWp": float(area) * efficiency_25,
                "Electricity_Generation_kWh_a": generation_sum,
                "Direct_Use_kWh_a": float(balance["direct_use_sum_kwh"]),
                "Battery_Use_kWh_a": float(balance["battery_to_load_sum_kwh"]),
                "Total_Usable_kWh_a": usable_sum,
                "Battery_Charge_from_PV_kWh_a": float(balance["battery_charge_input_sum_kwh"]),
                "Battery_Losses_kWh_a": float(balance["battery_losses_sum_kwh"]),
                "Battery_SOC_Year_End_kWh": float(balance["final_state_of_charge_kwh"]),
                "Feed_In_kWh_a": float(balance["feed_in_sum_kwh"]),
                "Grid_Import_kWh_a": float(balance["grid_import_sum_kwh"]),
                "Avoided_Purchase_Cost_EUR_a": economics["avoided_purchase_cost_eur"],
                "Feed_In_Revenue_EUR_a": economics["feed_in_revenue_eur"],
                "Total_Value_EUR_a": economics["total_value_eur"],
                "Self_Consumption_Rate_pct": 100.0 * usable_sum / generation_sum if generation_sum else 0.0,
                "Self_Sufficiency_Rate_pct": 100.0 * usable_sum / annual_load if annual_load else 0.0,
            })
    return pd.DataFrame(records)


def simulate_area_range(
    average_year: pd.DataFrame,
    load_kwh: pd.Series,
    areas_m2: np.ndarray,
    efficiency_25: float,
    temperature_coefficient_per_k: float,
    faiman_u0_wm2k: float,
    faiman_u1_wm2k_per_mps: float,
    optical_reflection_loss: float,
    other_system_loss: float,
    electricity_price_eur_per_kwh: float = 0.0,
    feed_in_tariff_eur_per_kwh: float = 0.0,
) -> pd.DataFrame:
    """Compatibility function: compare areas without a battery (0 kWh)."""
    return simulate_area_battery_range(
        average_year=average_year,
        load_kwh=load_kwh,
        areas_m2=areas_m2,
        battery_capacities_kwh=np.array([0.0]),
        efficiency_25=efficiency_25,
        temperature_coefficient_per_k=temperature_coefficient_per_k,
        faiman_u0_wm2k=faiman_u0_wm2k,
        faiman_u1_wm2k_per_mps=faiman_u1_wm2k_per_mps,
        optical_reflection_loss=optical_reflection_loss,
        other_system_loss=other_system_loss,
        electricity_price_eur_per_kwh=electricity_price_eur_per_kwh,
        feed_in_tariff_eur_per_kwh=feed_in_tariff_eur_per_kwh,
    )
