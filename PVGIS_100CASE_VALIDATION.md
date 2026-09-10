# Scientific 100-case PVGIS validation

## Objective

The benchmark compares the local PV model with a direct PVGIS 5.3 reference calculation for exactly 100 reproducible cases.

## Benchmark design

The default benchmark is a full 10 × 10 matrix:

- 10 fixed German locations;
- 10 fixed combinations of tilt, azimuth and nominal peak power.

This yields exactly 100 cases without random sampling. The case matrix can be exported, edited and re-imported as CSV.

## Two calculation paths

### Local model

1. PVGIS `seriescalc` is queried for a horizontal plane once per location.
2. The local code reconstructs/transposes irradiance to the entered module plane.
3. Module/cell temperature is calculated with the Faiman model.
4. Electrical energy is calculated from plane-of-array irradiance, STC module efficiency, temperature coefficient and system loss.

### PVGIS reference

For every case, one direct tilted-plane PVGIS `seriescalc` request is sent with:

- same latitude/longitude;
- same start/end years;
- same tilt and azimuth;
- same nominal `peakpower`;
- same user-entered system `loss`;
- `components=1` and `pvcalculation=1`.

This one request provides both `P` and the tilted radiation components `Gb(i)`, `Gd(i)` and `Gr(i)`.

## Quantities compared

- annual PV energy [kWh/a];
- annual specific PV yield [kWh/kWp·a];
- direct plane-of-array irradiation [kWh/m²·a];
- diffuse plane-of-array irradiation [kWh/m²·a];
- ground-reflected plane-of-array irradiation [kWh/m²·a];
- global plane-of-array irradiation [kWh/m²·a].

The sign convention is always `local model − PVGIS`.

## Scientific statistics

For energy, direct POA and global POA the project reports:

- linear regression slope and intercept;
- Pearson correlation coefficient r;
- coefficient of determination R²;
- mean bias error (MBE);
- mean absolute error (MAE);
- root mean square error (RMSE);
- normalized RMSE;
- mean absolute percentage error (MAPE).

The Streamlit dashboard also provides a Bland–Altman plot for energy agreement and regression plots of relative energy error against benchmark parameters.

### Error-driver correlations

The relative annual energy error is correlated only with the independent benchmark inputs:

- latitude;
- longitude;
- module tilt;
- azimuth deviation from south;
- nominal peak power.

**Global POA is deliberately excluded from this error-driver correlation analysis.** It remains a validation output for the direct model-vs-PVGIS irradiance comparison, but it is not treated as an independent explanatory parameter.

## Interpretation limitation

The local model uses PVGIS horizontal weather as input. Therefore the comparison does **not** independently validate the meteorological radiation database. It isolates differences introduced by the local irradiance transposition and the local electrical/temperature model versus the direct PVGIS calculation.
