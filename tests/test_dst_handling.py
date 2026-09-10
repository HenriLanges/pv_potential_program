import pandas as pd

from pv_model import utc_to_local_hour


def test_dst_fallback_is_rounded_in_utc_without_ambiguous_error():
    # Both UTC timestamps correspond to the same local time, 02:00, when daylight
    # saving time ends: once in CEST and once in CET.
    time_utc = pd.Series(
        pd.to_datetime(
            ["2014-10-26 00:10:00+00:00", "2014-10-26 01:10:00+00:00"],
            utc=True,
        )
    )

    local = utc_to_local_hour(time_utc, "Europe/Berlin")

    assert list(local) == [
        pd.Timestamp("2014-10-26 02:00:00"),
        pd.Timestamp("2014-10-26 02:00:00"),
    ]
