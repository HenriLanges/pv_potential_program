"""Simple hourly battery model for PV surplus and load deficit."""

from __future__ import annotations

import numpy as np


def simulate_battery_dispatch(
    generation_kwh: np.ndarray,
    load_kwh: np.ndarray,
    capacity_kwh: float,
    charge_efficiency: float = 0.95,
    discharge_efficiency: float | None = None,
    initial_state_of_charge_kwh: float = 0.0,
) -> dict[str, np.ndarray | float]:
    """Simulate direct use, charging, discharging, feed-in, and grid import.

    The battery is charged exclusively from PV surplus and discharged when load
    exceeds PV generation. Charging and discharging power are intentionally not
    limited in this simplified model.
    """
    generation = np.maximum(np.asarray(generation_kwh, dtype=float), 0.0)
    load = np.maximum(np.asarray(load_kwh, dtype=float), 0.0)
    if generation.shape != load.shape:
        raise ValueError("PV and load time series do not have the same length.")

    capacity = float(capacity_kwh)
    eta_charge = float(charge_efficiency)
    eta_discharge = (
        eta_charge if discharge_efficiency is None else float(discharge_efficiency)
    )
    if capacity < 0.0:
        raise ValueError("Battery capacity must not be negative.")
    if not 0.0 < eta_charge <= 1.0 or not 0.0 < eta_discharge <= 1.0:
        raise ValueError("Charge and discharge efficiencies must be between 0 and 1.")

    state_of_charge = float(np.clip(initial_state_of_charge_kwh, 0.0, capacity))
    direct_use = np.minimum(generation, load)
    battery_charge_input = np.zeros_like(generation)
    battery_to_load = np.zeros_like(generation)
    feed_in = np.zeros_like(generation)
    grid_import = np.zeros_like(generation)
    state_of_charge_series = np.zeros_like(generation)
    battery_losses = np.zeros_like(generation)

    for index in range(len(generation)):
        surplus = max(generation[index] - direct_use[index], 0.0)
        deficit = max(load[index] - direct_use[index], 0.0)

        free_capacity = max(capacity - state_of_charge, 0.0)
        charge_from_pv = min(surplus, free_capacity / eta_charge)
        stored_energy = charge_from_pv * eta_charge
        state_of_charge += stored_energy

        possible_output = state_of_charge * eta_discharge
        output_to_load = min(deficit, possible_output)
        withdrawn_energy = output_to_load / eta_discharge
        state_of_charge -= withdrawn_energy
        state_of_charge = float(np.clip(state_of_charge, 0.0, capacity))

        battery_charge_input[index] = charge_from_pv
        battery_to_load[index] = output_to_load
        feed_in[index] = max(surplus - charge_from_pv, 0.0)
        grid_import[index] = max(deficit - output_to_load, 0.0)
        state_of_charge_series[index] = state_of_charge
        battery_losses[index] = (charge_from_pv - stored_energy) + (
            withdrawn_energy - output_to_load
        )

    usable_energy = direct_use + battery_to_load
    return {
        "direct_use_kwh": direct_use,
        "battery_charge_input_kwh": battery_charge_input,
        "battery_to_load_kwh": battery_to_load,
        "usable_energy_kwh": usable_energy,
        "feed_in_kwh": feed_in,
        "grid_import_kwh": grid_import,
        "state_of_charge_kwh": state_of_charge_series,
        "battery_losses_kwh": battery_losses,
        "generation_sum_kwh": float(generation.sum()),
        "direct_use_sum_kwh": float(direct_use.sum()),
        "battery_charge_input_sum_kwh": float(battery_charge_input.sum()),
        "battery_to_load_sum_kwh": float(battery_to_load.sum()),
        "usable_energy_sum_kwh": float(usable_energy.sum()),
        "feed_in_sum_kwh": float(feed_in.sum()),
        "grid_import_sum_kwh": float(grid_import.sum()),
        "battery_losses_sum_kwh": float(battery_losses.sum()),
        "final_state_of_charge_kwh": float(state_of_charge),
        "annual_load_kwh": float(load.sum()),
    }
