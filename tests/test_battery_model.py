import numpy as np
import pytest

from pv_model import simulate_battery_dispatch


def test_surplus_is_stored_and_used_in_later_deficit():
    result = simulate_battery_dispatch(
        generation_kwh=np.array([2.0, 0.0]),
        load_kwh=np.array([1.0, 1.0]),
        capacity_kwh=1.0,
        charge_efficiency=1.0,
        discharge_efficiency=1.0,
    )
    assert result["direct_use_sum_kwh"] == pytest.approx(1.0)
    assert result["battery_to_load_sum_kwh"] == pytest.approx(1.0)
    assert result["grid_import_sum_kwh"] == pytest.approx(0.0)
    assert result["feed_in_sum_kwh"] == pytest.approx(0.0)


def test_zero_capacity_matches_direct_use_without_storage():
    result = simulate_battery_dispatch(
        generation_kwh=np.array([2.0, 0.0]),
        load_kwh=np.array([1.0, 1.0]),
        capacity_kwh=0.0,
    )
    assert result["battery_to_load_sum_kwh"] == pytest.approx(0.0)
    assert result["feed_in_sum_kwh"] == pytest.approx(1.0)
    assert result["grid_import_sum_kwh"] == pytest.approx(1.0)
