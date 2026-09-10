"""Scientific Streamlit dashboard for a reproducible 100-case PVGIS validation."""
from __future__ import annotations

import io
import json

import numpy as np
import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt

from pv_model.pvgis_100case_validation import default_100_cases, run_100_case_validation, validate_case_table
from pv_model.validation_plots import (
    bland_altman_figure,
    error_distribution_figure,
    error_driver_figure,
    regression_figure,
)

st.set_page_config(page_title="PVGIS 100-case scientific validation", layout="wide")
st.title("PVGIS vs. local PV model — 100-case validation")
st.caption("Reproducible benchmark of irradiance transposition and PV-energy calculation against PVGIS 5.3.")
st.info(
    "Interpretation: the local model uses horizontal PVGIS weather as meteorological input. "
    "Therefore this benchmark validates the local transposition and electrical model against the "
    "direct PVGIS tilted-plane/PV calculation; it is not an independent validation of the weather database."
)

with st.sidebar:
    st.header("Benchmark")
    source = st.radio("Cases", ["Default 100-case benchmark", "Upload custom 100-case CSV"])
    uploaded = None
    if source.startswith("Upload"):
        uploaded = st.file_uploader("Case CSV", type=["csv"])
    template = default_100_cases()
    st.download_button("Download 100-case template", template.to_csv(index=False), "pvgis_100case_template.csv", "text/csv")

    st.header("PVGIS period")
    start_year = st.number_input("Start year", 2005, 2023, 2014, 1)
    end_year = st.number_input("End year", 2005, 2023, 2023, 1)

    st.header("Local model parameters")
    efficiency_pct = st.number_input("Module efficiency at STC [%]", 5.0, 35.0, 20.0, 0.1)
    temp_coeff_pct = st.number_input("Pmax temperature coefficient [%/K]", -1.0, 0.0, -0.40, 0.01)
    system_loss_pct = st.number_input("System loss used in both calculations [%]", 0.0, 50.0, 14.0, 0.5)
    albedo = st.number_input("Ground albedo [-]", 0.0, 1.0, 0.20, 0.01)
    with st.expander("Faiman / advanced"):
        u0 = st.number_input("Faiman U0 [W/(m² K)]", 1.0, 100.0, 25.0, 0.5)
        u1 = st.number_input("Faiman U1 [W/(m² K)/(m/s)]", 0.0, 30.0, 6.84, 0.1)
        optical_loss_pct = st.number_input("Additional optical loss in local model [%]", 0.0, 30.0, 0.0, 0.1)
    run = st.button("Run 100-case validation", type="primary", use_container_width=True)

if "validation_results" not in st.session_state:
    st.session_state.validation_results = None

if run:
    try:
        if uploaded is None:
            cases = template
        else:
            cases = validate_case_table(pd.read_csv(uploaded), require_100=True)
        progress = st.progress(0.0, text="Preparing benchmark …")
        status = st.empty()
        def update(done, total, message):
            progress.progress(min(max(done / max(total, 1), 0.0), 1.0), text=message)
            status.caption(message)
        results, stats, drivers = run_100_case_validation(
            cases=cases,
            start_year=int(start_year),
            end_year=int(end_year),
            efficiency_25=efficiency_pct / 100.0,
            temperature_coefficient_per_k=temp_coeff_pct / 100.0,
            faiman_u0_wm2k=u0,
            faiman_u1_wm2k_per_mps=u1,
            ground_albedo=albedo,
            system_loss_pct=system_loss_pct,
            optical_reflection_loss_pct=optical_loss_pct,
            progress_callback=update,
        )
        progress.progress(1.0, text="100/100 cases completed")
        st.session_state.validation_results = (results, stats, drivers)
    except Exception as exc:
        st.exception(exc)

if st.session_state.validation_results is None:
    st.subheader("Benchmark design")
    st.write("The default matrix contains exactly 10 locations × 10 tilt/azimuth/kWp configurations = 100 reproducible cases.")
    st.dataframe(template, use_container_width=True, hide_index=True)
    st.stop()

results, stats, drivers = st.session_state.validation_results
energy = stats["energy"]

st.subheader("Summary")
c1, c2, c3, c4, c5, c6 = st.columns(6)
c1.metric("Cases", f"{len(results)}")
c2.metric("Energy MBE", f"{energy['mbe']:.1f} kWh/a")
c3.metric("Energy MAE", f"{energy['mae']:.1f} kWh/a")
c4.metric("Energy RMSE", f"{energy['rmse']:.1f} kWh/a")
c5.metric("Energy MAPE", f"{energy['mape']:.2f} %")
c6.metric("Energy R²", f"{energy['r2']:.4f}")

st.caption(
    "Error sign convention: Model − PVGIS. Positive values mean that the local model predicts more energy/irradiation than PVGIS."
)

tab1, tab2, tab3, tab4, tab5 = st.tabs(["Energy agreement", "Irradiance agreement", "Error drivers", "Case results", "Method / export"])

with tab1:
    col1, col2 = st.columns(2)
    with col1:
        fig = regression_figure(results, "pvgis_energy_kwh_a", "model_energy_kwh_a", "PVGIS energy [kWh/a]", "Model energy [kWh/a]", "Annual PV energy: model vs PVGIS")
        st.pyplot(fig); plt.close(fig)
    with col2:
        fig = bland_altman_figure(results)
        st.pyplot(fig); plt.close(fig)
    col3, col4 = st.columns(2)
    with col3:
        fig = regression_figure(results, "pvgis_specific_yield_kwh_kwp_a", "model_specific_yield_kwh_kwp_a", "PVGIS specific yield [kWh/kWp·a]", "Model specific yield [kWh/kWp·a]", "Specific PV yield: model vs PVGIS")
        st.pyplot(fig); plt.close(fig)
    with col4:
        fig = error_distribution_figure(results)
        st.pyplot(fig); plt.close(fig)

with tab2:
    c1, c2 = st.columns(2)
    with c1:
        fig = regression_figure(results, "pvgis_direct_poa_kwh_m2_a", "model_direct_poa_kwh_m2_a", "PVGIS direct POA [kWh/m²·a]", "Model direct POA [kWh/m²·a]", "Direct in-plane irradiation")
        st.pyplot(fig); plt.close(fig)
    with c2:
        fig = regression_figure(results, "pvgis_global_poa_kwh_m2_a", "model_global_poa_kwh_m2_a", "PVGIS global POA [kWh/m²·a]", "Model global POA [kWh/m²·a]", "Global in-plane irradiation")
        st.pyplot(fig); plt.close(fig)
    st.dataframe(pd.DataFrame({
        "comparison": ["Energy", "Specific yield", "Direct POA", "Global POA"],
        "R2": [stats["energy"]["r2"], stats["specific_yield"]["r2"], stats["direct_poa"]["r2"], stats["global_poa"]["r2"]],
        "slope": [stats["energy"]["slope"], stats["specific_yield"]["slope"], stats["direct_poa"]["slope"], stats["global_poa"]["slope"]],
        "MBE": [stats["energy"]["mbe"], stats["specific_yield"]["mbe"], stats["direct_poa"]["mbe"], stats["global_poa"]["mbe"]],
        "RMSE": [stats["energy"]["rmse"], stats["specific_yield"]["rmse"], stats["direct_poa"]["rmse"], stats["global_poa"]["rmse"]],
        "MAPE_pct": [stats["energy"]["mape"], stats["specific_yield"]["mape"], stats["direct_poa"]["mape"], stats["global_poa"]["mape"]],
    }), use_container_width=True, hide_index=True)

with tab3:
    st.write("Linear correlations of independent benchmark parameters with relative energy error. Global POA is intentionally excluded from the correlation-driver analysis because it is a model/reference output rather than an independent benchmark input.")
    st.dataframe(drivers, use_container_width=True, hide_index=True)
    labels = {
        "latitude": ("Latitude [°]", "Energy error vs latitude"),
        "longitude": ("Longitude [°]", "Energy error vs longitude"),
        "tilt_deg": ("Module tilt [°]", "Energy error vs module tilt"),
        "azimuth_deviation_south_deg": ("Azimuth deviation from south [°]", "Energy error vs orientation"),
        "peak_power_kwp": ("Nominal power [kWp]", "Energy error vs system size"),
    }
    selected = st.selectbox("X parameter", list(labels), format_func=lambda k: labels[k][0])
    fig = error_driver_figure(results, selected, "energy_error_pct", labels[selected][0], "Relative energy error [%]", labels[selected][1])
    st.pyplot(fig); plt.close(fig)

with tab4:
    display_cols = [
        "case_id", "location", "latitude", "longitude", "tilt_deg", "azimuth_deg", "peak_power_kwp",
        "model_energy_kwh_a", "pvgis_energy_kwh_a", "energy_error", "energy_error_pct",
        "model_direct_poa_kwh_m2_a", "pvgis_direct_poa_kwh_m2_a", "direct_poa_error_pct",
        "model_global_poa_kwh_m2_a", "pvgis_global_poa_kwh_m2_a", "global_poa_error_pct",
    ]
    st.dataframe(results[display_cols], use_container_width=True, hide_index=True)

with tab5:
    st.markdown("""
**Comparison design**

- Local path: horizontal PVGIS weather → local solar geometry/transposition → Faiman cell temperature → local electrical conversion.
- Reference path: direct PVGIS tilted-plane request with `pvcalculation=1`, identical tilt, azimuth, kWp, years and system-loss input.
- PVGIS `P` is treated as hourly mean power in W and integrated to kWh/a.
- Irradiance components are integrated from W/m² to kWh/m²·a.
- Leap-day hours are excluded before calculating the mean annual sum so years have equal statistical weight.
- A regression is not interpreted alone: bias, MAE/RMSE/MAPE and Bland–Altman limits are shown as agreement measures.
""")
    st.download_button("Download all 100 case results (CSV)", results.to_csv(index=False), "pvgis_100case_results.csv", "text/csv")
    st.download_button("Download error-driver correlations (CSV)", drivers.to_csv(index=False), "pvgis_error_driver_correlations.csv", "text/csv")
    st.download_button("Download summary statistics (JSON)", json.dumps(stats, indent=2), "pvgis_validation_statistics.json", "application/json")
