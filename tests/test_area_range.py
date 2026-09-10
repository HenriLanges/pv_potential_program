import numpy as np


def test_area_example_contains_boundaries_and_five_intermediate_steps():
    areas = np.linspace(10.0, 20.0, 5 + 1)
    assert np.allclose(areas, [10, 12, 14, 16, 18, 20])
