import numpy as np
import pandas as pd

from pv_model import (
    optimize_module_angles,
    plane_irradiance_components,
    solar_geometry,
)


def synthetic_horizontal_year() -> pd.DataFrame:
    times = pd.date_range(
        "2025-01-01", "2026-01-01", freq="h", inclusive="left", tz="UTC"
    )
    geometry = solar_geometry(times, latitude=52.52, longitude=13.405)
    cos_zenith = geometry["cos_zenith"].to_numpy()
    daylight = cos_zenith > 0.0
    beam_horizontal = 800.0 * cos_zenith
    diffuse_horizontal = np.where(daylight, 100.0, 0.0)

    return pd.DataFrame(
        {
            "time_utc": times,
            "time_local": times.tz_convert("Europe/Berlin").tz_localize(None),
            "beam_horizontal_wm2": beam_horizontal,
            "diffuse_horizontal_wm2": diffuse_horizontal,
            "global_horizontal_wm2": beam_horizontal + diffuse_horizontal,
            "ambient_temperature_c": np.full(len(times), 10.0),
            "wind_speed_mps": np.full(len(times), 2.0),
            "solar_zenith_deg": geometry["solar_zenith_deg"].to_numpy(),
            "solar_azimuth_deg": geometry["solar_azimuth_deg"].to_numpy(),
            "cos_zenith": cos_zenith,
            "dni_wm2": np.where(daylight, 800.0, 0.0),
        }
    )


def test_horizontal_plane_reproduces_horizontal_irradiance():
    data = synthetic_horizontal_year().iloc[:100]
    poa, direct, diffuse, reflected = plane_irradiance_components(
        data, tilt_deg=0.0, azimuth_deg=0.0, ground_albedo=0.2
    )

    assert np.allclose(direct, data["beam_horizontal_wm2"])
    assert np.allclose(diffuse, data["diffuse_horizontal_wm2"])
    assert np.allclose(reflected, 0.0)
    assert np.allclose(poa, data["global_horizontal_wm2"])


def test_iterative_search_finds_south_facing_solution_for_berlin_like_data():
    result = optimize_module_angles(
        horizontal_data=synthetic_horizontal_year(),
        efficiency_25=0.20,
        temperature_coefficient_per_k=-0.004,
        faiman_u0_wm2k=25.0,
        faiman_u1_wm2k_per_mps=6.84,
        optical_reflection_loss=0.0,
        other_system_loss=0.0,
        ground_albedo=0.2,
    )

    azimuth_distance_to_south = abs(
        ((float(result["azimuth_deg"]) - 180.0 + 180.0) % 360.0) - 180.0
    )
    assert 30.0 <= float(result["tilt_deg"]) <= 60.0
    assert azimuth_distance_to_south <= 15.0
    assert int(result["evaluated_candidates"]) > 100
