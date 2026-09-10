from pv_model import (
    calculate_annual_economic_value,
    calculate_cell_temperature,
    compare_generation_with_load,
    fetch_pvgis_horizontal,
    optimize_module_angles,
    plane_irradiance_components,
    simulate_area_range,
    simulate_area_battery_range,
    simulate_battery_dispatch,
    solar_geometry,
)


def test_public_interface_keeps_main_functions_importable():
    functions = [
        calculate_annual_economic_value,
        calculate_cell_temperature,
        compare_generation_with_load,
        fetch_pvgis_horizontal,
        optimize_module_angles,
        plane_irradiance_components,
        simulate_area_range,
    simulate_area_battery_range,
    simulate_battery_dispatch,
        solar_geometry,
    ]
    assert all(callable(function) for function in functions)
