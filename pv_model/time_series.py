"""Time conversion and construction of an average weather year."""

from __future__ import annotations

import pandas as pd

from .constants import REFERENCE_YEAR


def utc_to_local_hour(time_utc: pd.Series, timezone: str) -> pd.Series:
    """Round in UTC and then return naive local hourly timestamps.

    Rounding before timezone conversion avoids the known ambiguity during the
    repeated hour when daylight saving time ends.
    """
    return time_utc.dt.round("h").dt.tz_convert(timezone).dt.tz_localize(None)


def make_average_year(
    hourly_data: pd.DataFrame,
    reference_year: int = REFERENCE_YEAR,
) -> pd.DataFrame:
    """Build an average non-leap year from multiple years."""
    if pd.Timestamp(reference_year, 12, 31).dayofyear != 365:
        raise ValueError("The reference year must have 365 days in this version.")

    required = {
        "time_local",
        "irradiance_poa_wm2",
        "ambient_temperature_c",
        "wind_speed_mps",
        "beam_wm2",
        "diffuse_wm2",
        "ground_reflected_wm2",
    }
    missing = required.difference(hourly_data.columns)
    if missing:
        raise ValueError(
            "Columns required for the average year are missing: " + ", ".join(sorted(missing))
        )

    data = hourly_data.copy()
    data = data[
        ~(
            (data["time_local"].dt.month == 2)
            & (data["time_local"].dt.day == 29)
        )
    ]
    data["month"] = data["time_local"].dt.month
    data["day"] = data["time_local"].dt.day
    data["hour"] = data["time_local"].dt.hour

    value_columns = [
        "irradiance_poa_wm2",
        "ambient_temperature_c",
        "wind_speed_mps",
        "beam_wm2",
        "diffuse_wm2",
        "ground_reflected_wm2",
    ]
    average = (
        data.groupby(["month", "day", "hour"], as_index=False)[value_columns]
        .mean(numeric_only=True)
    )

    index = pd.date_range(
        f"{reference_year}-01-01",
        f"{reference_year + 1}-01-01",
        freq="h",
        inclusive="left",
    )
    result = pd.DataFrame({"time": index})
    result["month"] = result["time"].dt.month
    result["day"] = result["time"].dt.day
    result["hour"] = result["time"].dt.hour
    result = result.merge(average, on=["month", "day", "hour"], how="left")

    if result["irradiance_poa_wm2"].isna().any():
        missing_hours = int(result["irradiance_poa_wm2"].isna().sum())
        raise ValueError(
            f"The averaged PVGIS year is missing {missing_hours} hourly values."
        )

    return result.drop(columns=["month", "day", "hour"])
