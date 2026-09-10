from pv_model import fetch_pvgis_horizontal


class FakeResponse:
    def raise_for_status(self):
        return None

    def json(self):
        return {
            "outputs": {
                "hourly": [
                    {
                        "time": "20140101:0000",
                        "Gb(i)": 0.0,
                        "Gd(i)": 0.0,
                        "Gr(i)": 0.0,
                        "T2m": 4.0,
                        "WS10m": 2.0,
                    }
                ]
            }
        }


def test_pvgis_is_requested_once_for_horizontal_components(monkeypatch):
    calls = []

    def fake_get(url, params, timeout):
        calls.append((url, params, timeout))
        return FakeResponse()

    monkeypatch.setattr("pv_model.api_request.requests.get", fake_get)
    data = fetch_pvgis_horizontal(52.52, 13.405)

    assert len(calls) == 1
    assert calls[0][1]["angle"] == 0.0
    assert calls[0][1]["aspect"] == 0.0
    assert len(data) == 1
