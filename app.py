"""Streamlit interface for PV potential, BDEW load profiles, and battery storage."""
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import streamlit as st

from geocoding import geocode_address, timezone_for_coordinates
from load_profiles import REFERENCE_YEAR, STATE_NAMES, create_hourly_load_profile
from pv_model import (
    END_YEAR,
    START_YEAR,
    annual_energy_per_m2_for_angles,
    compass_direction,
    fetch_pvgis_horizontal,
    make_average_year,
    optimize_module_angles,
    simulate_area_battery_range,
    weather_for_angles,
)

DATA_PATH = Path(__file__).parent / "data" / "bdew_standard_load_profiles_2025.csv"

st.set_page_config(page_title="PV Potential with Battery", layout="wide")
st.title("PV Potential, Self-Consumption, and Battery Storage")
st.caption("PVGIS 5.3, Faiman temperature model, and BDEW standard load profiles 2025.")
st.info("Weather basis: 2014–2023; an average year is derived from these data.")

with st.sidebar:
    st.header("Location")
    location_mode = st.radio(
        "Enter location as",
        ["Address or place", "Coordinates"],
        horizontal=True,
    )
    address = st.text_input(
        "Address or place",
        "Berlin, Germany",
        disabled=location_mode != "Address or place",
    )
    c1, c2 = st.columns(2)
    latitude_input = c1.number_input(
        "Latitude",
        -90.0,
        90.0,
        52.5200,
        format="%.6f",
        disabled=location_mode != "Coordinates",
    )
    longitude_input = c2.number_input(
        "Longitude",
        -180.0,
        180.0,
        13.4050,
        format="%.6f",
        disabled=location_mode != "Coordinates",
    )

    st.header("PV System")
    tilt = st.number_input("Tilt [°]", 0.0, 90.0, 30.0, 1.0)
    azimuth = st.number_input(
        "Azimuth [°] (0=N, 90=E, 180=S, 270=W)",
        0.0,
        360.0,
        180.0,
        5.0,
    )
    efficiency_pct = st.number_input(
        "Module efficiency at 25 °C [%]",
        1.0,
        40.0,
        20.0,
        0.1,
    )

    st.header("PV Area Range")
    min_area = st.number_input("Minimum PV area [m²]", 0.1, 1_000_000.0, 10.0, 1.0)
    max_area = st.number_input("Maximum PV area [m²]", 0.1, 1_000_000.0, 20.0, 1.0)
    area_steps = st.number_input("Number of PV area steps", 1, 100, 5, 1)
    if max_area >= min_area:
        area_preview = np.linspace(min_area, max_area, int(area_steps) + 1)
        st.caption("Areas: " + ", ".join(f"{x:g}" for x in area_preview) + " m²")

    st.header("Battery Range")
    min_battery = st.number_input(
        "Minimum battery capacity [kWh]",
        0.0,
        1_000_000.0,
        0.0,
        1.0,
    )
    max_battery = st.number_input(
        "Maximum battery capacity [kWh]",
        0.0,
        1_000_000.0,
        10.0,
        1.0,
    )
    battery_steps = st.number_input("Number of battery capacity steps", 1, 100, 5, 1)
    battery_efficiency_pct = st.number_input(
        "Charge/discharge efficiency per direction [%]",
        1.0,
        100.0,
        95.0,
        0.5,
    )
    if max_battery >= min_battery:
        battery_preview = np.linspace(min_battery, max_battery, int(battery_steps) + 1)
        st.caption(
            "Batteries: " + ", ".join(f"{x:g}" for x in battery_preview) + " kWh"
        )

    st.header("Electricity Consumption")
    profile = st.selectbox(
        "BDEW profile",
        ["H25", "G25", "L25"],
        format_func=lambda x: {
            "H25": "H25 – Household",
            "G25": "G25 – Commercial",
            "L25": "L25 – Agriculture",
        }[x],
    )
    annual_consumption = st.number_input(
        "Annual electricity consumption [kWh/a]",
        1.0,
        1_000_000_000.0,
        4_000.0,
        100.0,
    )
    state_code = st.selectbox(
        "German federal state for public holidays",
        list(STATE_NAMES),
        format_func=lambda code: STATE_NAMES[code],
    )
    include_assumption_day = (
        st.checkbox("Include Assumption Day", False) if state_code == "BY" else False
    )

    st.header("Economics")
    electricity_price = st.number_input(
        "Electricity purchase price [€/kWh]",
        0.0,
        10.0,
        0.35,
        0.01,
        format="%.3f",
    )
    feed_in_tariff = st.number_input(
        "Feed-in tariff [€/kWh]",
        0.0,
        10.0,
        0.08,
        0.01,
        format="%.3f",
    )

    with st.expander("Advanced PV system parameters"):
        temperature_coefficient_pct = st.number_input(
            "Pmax temperature coefficient [%/K]",
            -2.0,
            0.0,
            -0.4,
            0.01,
        )
        faiman_u0 = st.number_input("Faiman U0 [W/(m²·K)]", 1.0, 100.0, 25.0, 0.5)
        faiman_u1 = st.number_input(
            "Faiman U1 [W/(m²·K)/(m/s)]",
            0.0,
            30.0,
            6.84,
            0.1,
        )
        ground_albedo = st.number_input("Ground reflectance / albedo [-]", 0.0, 1.0, 0.20, 0.01)
        reflection_loss_pct = st.number_input(
            "Additional optical reflection loss [%]",
            0.0,
            30.0,
            0.0,
            0.1,
        )
        other_loss_pct = st.number_input("Other system losses [%]", 0.0, 50.0, 0.0, 0.5)

    calculate = st.button("Calculate", type="primary", use_container_width=True)


@st.cache_data(show_spinner=False)
def cached_geocode(text):
    return geocode_address(text)


@st.cache_data(show_spinner=False)
def cached_weather(lat, lon, timezone):
    return fetch_pvgis_horizontal(lat, lon, timezone=timezone)


@st.cache_data(show_spinner=False)
def cached_load(profile_name, consumption, federal_state, assumption_day):
    return create_hourly_load_profile(
        DATA_PATH,
        profile_name,
        consumption,
        federal_state,
        REFERENCE_YEAR,
        assumption_day,
    )


def resolve_location():
    if location_mode == "Address or place":
        return cached_geocode(address)
    return "Manually entered coordinates", float(latitude_input), float(longitude_input)


def line_plot_by_battery(results, y_column, title, y_label):
    fig, ax = plt.subplots(figsize=(7, 4))
    for capacity, group in results.groupby("Battery_kWh"):
        ax.plot(group["Area_m2"], group[y_column], marker="o", label=f"{capacity:g} kWh")
    ax.set(title=title, xlabel="PV area [m²]", ylabel=y_label)
    ax.grid(True, alpha=0.3)
    ax.legend(title="Battery", fontsize=8)
    fig.tight_layout()
    st.pyplot(fig)
    plt.close(fig)


def generation_plot(results):
    data = results.drop_duplicates("Area_m2")
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.plot(data["Area_m2"], data["Electricity_Generation_kWh_a"], marker="o")
    ax.set(
        title="PV Area and Total Electricity Generation",
        xlabel="PV area [m²]",
        ylabel="Electricity generation [kWh/a]",
    )
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    st.pyplot(fig)
    plt.close(fig)


def battery_bar_plot(area_results, area):
    data = area_results.sort_values("Battery_kWh")
    x = np.arange(len(data))
    direct = data["Direct_Use_kWh_a"].to_numpy()
    battery = data["Battery_Use_kWh_a"].to_numpy()
    grid = data["Grid_Import_kWh_a"].to_numpy()
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.bar(x, direct, label="Direct PV use")
    ax.bar(x, battery, bottom=direct, label="Use via battery")
    ax.bar(x, grid, bottom=direct + battery, label="Grid import")
    ax.set_xticks(x, [f"{v:g}" for v in data["Battery_kWh"]])
    ax.set_xlabel("Battery capacity [kWh]")
    ax.set_ylabel("Energy [kWh/a]")
    ax.set_title(f"Supply at {area:g} m² PV area")
    ax.legend(fontsize=8)
    fig.tight_layout()
    st.pyplot(fig)
    plt.close(fig)


if calculate:
    if max_area < min_area or max_battery < min_battery:
        st.error("Maximum values must be at least as large as minimum values.")
        st.stop()

    areas = np.unique(np.linspace(min_area, max_area, int(area_steps) + 1))
    batteries = np.unique(np.linspace(min_battery, max_battery, int(battery_steps) + 1))

    try:
        with st.spinner("Calculating PVGIS data and all combinations …"):
            location_name, latitude, longitude = resolve_location()
            local_timezone = timezone_for_coordinates(latitude, longitude)
            horizontal = cached_weather(latitude, longitude, local_timezone)
            selected = weather_for_angles(horizontal, tilt, azimuth, ground_albedo)
            weather = make_average_year(selected)
            angle_hint = optimize_module_angles(
                horizontal,
                efficiency_pct / 100,
                temperature_coefficient_pct / 100,
                faiman_u0,
                faiman_u1,
                reflection_loss_pct / 100,
                other_loss_pct / 100,
                ground_albedo,
            )
            selected_yield = annual_energy_per_m2_for_angles(
                horizontal,
                tilt,
                azimuth,
                efficiency_pct / 100,
                temperature_coefficient_pct / 100,
                faiman_u0,
                faiman_u1,
                reflection_loss_pct / 100,
                other_loss_pct / 100,
                ground_albedo,
            )
            load = cached_load(profile, annual_consumption, state_code, include_assumption_day)
            results = simulate_area_battery_range(
                weather,
                load,
                areas,
                batteries,
                efficiency_pct / 100,
                temperature_coefficient_pct / 100,
                faiman_u0,
                faiman_u1,
                reflection_loss_pct / 100,
                other_loss_pct / 100,
                battery_efficiency_pct / 100,
                battery_efficiency_pct / 100,
                electricity_price,
                feed_in_tariff,
            )
    except Exception as exc:
        st.error(f"Calculation failed: {exc}")
        st.stop()

    st.success(
        f"{len(areas)} PV areas × {len(batteries)} battery sizes = {len(results)} variants."
    )
    st.caption(
        f"Location: {location_name} · {latitude:.6f}, {longitude:.6f} · Weather {START_YEAR}–{END_YEAR}"
    )
    improvement = (
        100
        * (float(angle_hint["annual_energy_kwh_per_m2"]) - selected_yield)
        / selected_yield
        if selected_yield
        else 0
    )
    st.info(
        "Optimal orientation as a reference: "
        f"{angle_hint['tilt_deg']:.0f}° tilt, "
        f"{angle_hint['azimuth_deg']:.0f}° "
        f"({compass_direction(float(angle_hint['azimuth_deg']))}), "
        f"about {improvement:+.1f}% compared with the entered orientation."
    )

    best_case = results[
        (results["Area_m2"] == areas.max())
        & (results["Battery_kWh"] == batteries.max())
    ].iloc[0]
    c1, c2, c3, c4 = st.columns(4)
    c1.metric(
        "PV generation",
        f"{best_case['Electricity_Generation_kWh_a']:,.0f} kWh/a",
    )
    c2.metric("Total usable", f"{best_case['Total_Usable_kWh_a']:,.0f} kWh/a")
    c3.metric("Grid import", f"{best_case['Grid_Import_kWh_a']:,.0f} kWh/a")
    c4.metric(
        "Self-sufficiency rate",
        f"{best_case['Self_Sufficiency_Rate_pct']:.1f} %",
    )

    st.subheader("Results")
    st.dataframe(
        results.style.format({c: "{:,.2f}" for c in results.columns if c not in []}),
        use_container_width=True,
    )

    left, right = st.columns(2)
    with left:
        generation_plot(results)
    with right:
        line_plot_by_battery(
            results,
            "Total_Usable_kWh_a",
            "Usable Energy by Battery Size",
            "Usable energy [kWh/a]",
        )

    left, right = st.columns(2)
    with left:
        line_plot_by_battery(
            results,
            "Feed_In_kWh_a",
            "Feed-In",
            "Feed-in [kWh/a]",
        )
    with right:
        line_plot_by_battery(
            results,
            "Grid_Import_kWh_a",
            "Grid Import",
            "Grid import [kWh/a]",
        )

    line_plot_by_battery(
        results,
        "Total_Value_EUR_a",
        "Annual Gross Value",
        "Gross value [€/a]",
    )

    st.subheader("Supply Shares by PV Area")
    plot_columns = st.columns(2)
    for index, area in enumerate(areas):
        with plot_columns[index % 2]:
            battery_bar_plot(results[results["Area_m2"] == area], float(area))

    st.download_button(
        "Download result table as CSV",
        results.to_csv(index=False, sep=";").encode("utf-8"),
        "pv_area_battery_comparison.csv",
        "text/csv",
    )

    with st.expander("Methodological Notes and Limitations"):
        st.markdown(
            """
- The Faiman model uses plane-of-array irradiance, PVGIS air temperature `T2m`, and wind speed `WS10m`.
- The battery starts empty, is charged only from PV surplus, and is discharged when load exceeds PV generation.
- Charging/discharging power limits, self-discharge, degradation, minimum reserve, and battery costs are not modelled.
- Direct PV use plus battery-supplied energy plus grid import equals the supplied annual load.
- Gross value includes avoided electricity purchase costs and feed-in revenue, but no investment or operating costs.
"""
        )
else:
    st.write("Enter parameters in the sidebar and select **Calculate**.")
