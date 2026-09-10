# Architecture

The structure of the original modularized project is preserved.

- `app.py`: Streamlit inputs, result presentation, and CSV export
- `geocoding.py`: address and coordinate lookup
- `load_profiles.py`: BDEW standard load profiles
- `pv_model/api_request.py`: one horizontal PVGIS request including `T2m` and `WS10m`
- `pv_model/solar_geometry.py`: solar position
- `pv_model/radiation.py`: conversion to the tilted module plane
- `pv_model/temperature_model.py`: Faiman temperature model
- `pv_model/energy_production.py`: electrical PV generation
- `pv_model/battery_model.py`: hourly charging and discharging
- `pv_model/simulation.py`: combination of every PV area with every battery size
- `pv_model/economics.py`: avoided electricity purchase costs and feed-in revenue
- `pv_model/angle_optimization.py`: local angle optimization without additional PVGIS requests

## Calculation Sequence

1. PVGIS weather data are loaded once per location.
2. Irradiance is converted to the entered module plane.
3. The Faiman model calculates module temperature from POA irradiance, `T2m`, and `WS10m`.
4. An hourly PV generation series is created for each PV area.
5. The same generation series is simulated with every selected battery capacity.
6. For each hour: direct PV use, charging from surplus, discharging during a deficit, then grid import or feed-in.

## PVGIS 100-case system-validation layer

- `pv_model/pvgis_validation.py`: independent tilted-plane/PV-output PVGIS reference request and parsing.
- `pv_model/pvgis_100case_validation.py`: fixed 100-case benchmark and model/reference comparison.
- `pv_model/validation_statistics.py`: agreement statistics and error-driver correlations.
- `pv_model/validation_plots.py`: regression, Bland–Altman, distribution, and error-driver figures.
- `pvgis_100case_validation_app.py`: separate Streamlit validation dashboard.
- `run_pvgis_100case_validation.py`: command-line system-test runner.

Global POA is retained as a validation output but excluded from the error-driver correlation parameter set.

