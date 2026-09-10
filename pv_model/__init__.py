"""Public interface of the modular PV, load, and battery model."""

from .angle_optimization import optimize_module_angles
from .api_request import PVGISRequestError, fetch_pvgis_horizontal, fetch_pvgis_hourly
from .battery_model import simulate_battery_dispatch
from .constants import END_YEAR, PVGIS_URL, REFERENCE_YEAR, START_YEAR
from .economics import calculate_annual_economic_value
from .energy_production import annual_energy_per_m2_for_angles, electrical_energy_kwh, pv_energy_for_area
from .load_comparison import compare_generation_with_load
from .pvgis_validation import (
    add_pvgis_scaled_generation_columns,
    energy_comparison_summary,
    fetch_pvgis_pv_output,
    fetch_pvgis_tilted_radiation,
    pvgis_mean_annual_energy_kwh,
    radiation_comparison_summary,
)
from .radiation import plane_irradiance_components, weather_for_angles
from .simulation import simulate_area_battery_range, simulate_area_range
from .solar_geometry import compass_direction, compass_to_pvgis_aspect, solar_geometry
from .temperature_model import calculate_cell_temperature, temperature_adjusted_efficiency
from .time_series import make_average_year, utc_to_local_hour

__all__ = [
    "END_YEAR", "PVGIS_URL", "REFERENCE_YEAR", "START_YEAR", "PVGISRequestError",
    "annual_energy_per_m2_for_angles", "calculate_annual_economic_value",
    "calculate_cell_temperature", "compare_generation_with_load", "compass_direction",
    "compass_to_pvgis_aspect", "electrical_energy_kwh", "fetch_pvgis_horizontal",
    "fetch_pvgis_hourly", "make_average_year", "optimize_module_angles",
    "plane_irradiance_components", "pv_energy_for_area", "simulate_area_battery_range",
    "simulate_area_range", "simulate_battery_dispatch", "solar_geometry",
    "temperature_adjusted_efficiency", "utc_to_local_hour", "weather_for_angles",
    "add_pvgis_scaled_generation_columns", "energy_comparison_summary",
    "fetch_pvgis_pv_output", "fetch_pvgis_tilted_radiation",
    "pvgis_mean_annual_energy_kwh", "radiation_comparison_summary",
]

from .pvgis_100case_validation import default_100_cases, run_100_case_validation, validate_case_table
from .validation_statistics import error_driver_statistics, regression_statistics
from .validation_plots import bland_altman_figure, error_distribution_figure, error_driver_figure, regression_figure
__all__ += [
    "default_100_cases", "run_100_case_validation", "validate_case_table",
    "error_driver_statistics", "regression_statistics", "regression_figure",
    "error_driver_figure", "error_distribution_figure", "bland_altman_figure",
]
