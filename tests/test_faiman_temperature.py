import numpy as np
import pytest
from pv_model import calculate_cell_temperature


def test_faiman_temperature_uses_wind_cooling():
    low_wind = calculate_cell_temperature(np.array([800.0]), np.array([20.0]), np.array([0.0]), 25.0, 6.84)[0]
    high_wind = calculate_cell_temperature(np.array([800.0]), np.array([20.0]), np.array([5.0]), 25.0, 6.84)[0]
    assert low_wind == pytest.approx(52.0)
    assert high_wind < low_wind
