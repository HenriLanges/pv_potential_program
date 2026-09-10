# Changes Compared with the Template

- NOCT was fully replaced by the Faiman model.
- PVGIS wind speed `WS10m` is taken from the same hourly request.
- New Faiman inputs `U0` and `U1` were added to Streamlit.
- A separate `pv_model/battery_model.py` module was added.
- Battery capacities are generated from minimum, maximum, and intermediate steps in the same way as PV areas.
- Every PV area is combined with every battery capacity.
- New result metrics: battery charging, battery use, total self-consumption, losses, and state of charge at year end.
- Additional stacked bar charts for each PV area show direct PV use, battery use, and grid import.
- Existing area, angle, load-profile, and economics logic is preserved.

## PVGIS 100-case system test

- Added a reproducible 100-case comparison against PVGIS 5.3 as a separate system-validation workflow.
- Added Streamlit and CLI runners plus validation statistics and plots.
- Kept Global POA in the direct irradiance comparison.
- Removed Global POA from the error-driver correlation analysis; correlations now use only independent benchmark inputs.
- Added the missing `pvlib` runtime dependency already required by `pv_model/solar_geometry.py`.

