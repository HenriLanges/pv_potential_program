import numpy as np
import pandas as pd
import pytest

from pv_model import simulate_area_battery_range


def test_every_area_is_combined_with_every_battery_capacity():
    weather = pd.DataFrame({
        "irradiance_poa_wm2": [1000.0, 0.0],
        "ambient_temperature_c": [25.0, 25.0],
        "wind_speed_mps": [1.0, 1.0],
    })
    load = pd.Series([0.5, 0.5])
    result = simulate_area_battery_range(
        average_year=weather,
        load_kwh=load,
        areas_m2=np.array([1.0, 2.0]),
        battery_capacities_kwh=np.array([0.0, 1.0, 2.0]),
        efficiency_25=1.0,
        temperature_coefficient_per_k=0.0,
        faiman_u0_wm2k=25.0,
        faiman_u1_wm2k_per_mps=6.84,
        optical_reflection_loss=0.0,
        other_system_loss=0.0,
        battery_charge_efficiency=1.0,
        battery_discharge_efficiency=1.0,
    )
    assert len(result) == 6
    assert set(zip(result["Area_m2"], result["Battery_kWh"])) == {
        (1.0, 0.0), (1.0, 1.0), (1.0, 2.0),
        (2.0, 0.0), (2.0, 1.0), (2.0, 2.0),
    }
    for _, row in result.iterrows():
        assert row["Direct_Use_kWh_a"] + row["Battery_Use_kWh_a"] + row["Grid_Import_kWh_a"] == pytest.approx(1.0)
