import sys
import types

import pandas as pd

# The project declares pvlib as a runtime dependency. The execution environment
# used for this isolated unit test does not have it installed, and these tests do
# not exercise solar-position calculations, so a minimal import stub is enough.
if "pvlib" not in sys.modules:
    pvlib_stub = types.ModuleType("pvlib")
    pvlib_stub.solarposition = types.SimpleNamespace()
    pvlib_stub.irradiance = types.SimpleNamespace()
    sys.modules["pvlib"] = pvlib_stub

from pv_model.pvgis_validation import (  # noqa: E402
    energy_comparison_summary,
    fetch_pvgis_pv_output,
    fetch_pvgis_tilted_radiation,
    radiation_comparison_summary,
)


class FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


def _payload(include_power=False):
    row = {
        "time": "20140101:1200",
        "Gb(i)": 500.0,
        "Gd(i)": 100.0,
        "Gr(i)": 10.0,
    }
    if include_power:
        row["P"] = 800.0
    return {"outputs": {"hourly": [row]}}


def test_tilted_radiation_request_uses_pvgis_aspect(monkeypatch):
    calls = []

    def fake_get(url, params, timeout):
        calls.append((url, params, timeout))
        return FakeResponse(_payload(False))

    monkeypatch.setattr("pv_model.pvgis_validation.requests.get", fake_get)
    frame = fetch_pvgis_tilted_radiation(
        52.52, 13.405, tilt_deg=35.0, azimuth_deg=90.0
    )

    assert len(calls) == 1
    params = calls[0][1]
    assert params["angle"] == 35.0
    assert params["aspect"] == -90.0
    assert params["pvcalculation"] == 0
    assert params["components"] == 1
    assert frame.loc[0, "pvgis_global_poa_wm2"] == 610.0


def test_pv_request_contains_peakpower_and_loss(monkeypatch):
    calls = []

    def fake_get(url, params, timeout):
        calls.append((url, params, timeout))
        return FakeResponse(_payload(True))

    monkeypatch.setattr("pv_model.pvgis_validation.requests.get", fake_get)
    frame = fetch_pvgis_pv_output(
        52.52,
        13.405,
        tilt_deg=30.0,
        azimuth_deg=180.0,
        peak_power_kwp=4.2,
        system_loss_pct=7.5,
    )

    params = calls[0][1]
    assert params["pvcalculation"] == 1
    assert params["peakpower"] == 4.2
    assert params["loss"] == 7.5
    assert params["aspect"] == 0.0
    assert frame.loc[0, "pvgis_power_w"] == 800.0


def test_radiation_and_energy_summary_math():
    times = pd.to_datetime(["2014-01-01 12:00", "2015-01-01 12:00"], utc=True)
    program = pd.DataFrame(
        {
            "time_utc": times,
            "beam_wm2": [600.0, 600.0],
            "diffuse_wm2": [100.0, 100.0],
            "ground_reflected_wm2": [20.0, 20.0],
            "irradiance_poa_wm2": [720.0, 720.0],
        }
    )
    pvgis = pd.DataFrame(
        {
            "time_utc": times,
            "pvgis_beam_poa_wm2": [500.0, 500.0],
            "pvgis_diffuse_poa_wm2": [100.0, 100.0],
            "pvgis_reflected_poa_wm2": [10.0, 10.0],
            "pvgis_global_poa_wm2": [610.0, 610.0],
            "pvgis_power_w": [1000.0, 1000.0],
        }
    )

    radiation = radiation_comparison_summary(program, pvgis)
    direct = radiation.loc[radiation["Metric"] == "Direct irradiation"].iloc[0]
    assert direct["Program_kWh_m2_a"] == 0.6
    assert direct["PVGIS_kWh_m2_a"] == 0.5
    assert round(direct["Difference_pct"], 6) == 20.0

    energy = energy_comparison_summary(1.2, pvgis, peak_power_kwp=2.0)
    assert energy["pvgis_energy_kwh_a"] == 1.0
    assert round(energy["difference_pct"], 6) == 20.0
    assert energy["pvgis_specific_yield_kwh_per_kwp_a"] == 0.5
