import numpy as np
import pandas as pd
import pytest

from pv_model import simulate_area_range


def test_direct_use_and_feed_in_are_valued_separately():
    average_year = pd.DataFrame(
        {
            "irradiance_poa_wm2": [1000.0, 1000.0],
            "ambient_temperature_c": [25.0, 25.0],
            "wind_speed_mps": [1.0, 1.0],
        }
    )
    load = pd.Series([1.0, 0.2])

    result = simulate_area_range(
        average_year=average_year,
        load_kwh=load,
        areas_m2=np.array([1.0]),
        efficiency_25=1.0,
        temperature_coefficient_per_k=0.0,
        faiman_u0_wm2k=25.0,
        faiman_u1_wm2k_per_mps=6.84,
        optical_reflection_loss=0.0,
        other_system_loss=0.0,
        electricity_price_eur_per_kwh=0.30,
        feed_in_tariff_eur_per_kwh=0.10,
    ).iloc[0]

    # Generation: 2 kWh; direct use: 1.2 kWh; feed-in: 0.8 kWh.
    assert result["Avoided_Purchase_Cost_EUR_a"] == pytest.approx(0.36)
    assert result["Feed_In_Revenue_EUR_a"] == pytest.approx(0.08)
    assert result["Total_Value_EUR_a"] == pytest.approx(0.44)
