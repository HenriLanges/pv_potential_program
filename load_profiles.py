"""Prepare the 2025 BDEW standard load profiles."""

from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

import pandas as pd

REFERENCE_YEAR = 2025
DYNAMIC_PROFILES = {"H25", "P25", "S25"}

STATE_NAMES = {
    "BW": "Baden-Wuerttemberg",
    "BY": "Bavaria",
    "BE": "Berlin",
    "BB": "Brandenburg",
    "HB": "Bremen",
    "HH": "Hamburg",
    "HE": "Hesse",
    "MV": "Mecklenburg-Western Pomerania",
    "NI": "Lower Saxony",
    "NW": "North Rhine-Westphalia",
    "RP": "Rhineland-Palatinate",
    "SL": "Saarland",
    "SN": "Saxony",
    "ST": "Saxony-Anhalt",
    "SH": "Schleswig-Holstein",
    "TH": "Thuringia",
}


def easter_sunday(year: int) -> date:
    """Calculate Easter Sunday according to the Gregorian calendar."""
    a = year % 19
    b = year // 100
    c = year % 100
    d = b // 4
    e = b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i = c // 4
    k = c % 4
    ell = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * ell) // 451
    month = (h + ell - 7 * m + 114) // 31
    day = ((h + ell - 7 * m + 114) % 31) + 1
    return date(year, month, day)


def german_holidays(
    year: int,
    state_code: str,
    include_assumption_day: bool = False,
) -> set[date]:
    """Return public holidays for a German federal state.

    Holidays limited to specific municipalities are not detected automatically.
    In Bavaria, Assumption Day can therefore be enabled separately.
    """
    if state_code not in STATE_NAMES:
        raise ValueError("Unknown German federal-state code.")

    easter = easter_sunday(year)
    days = {
        date(year, 1, 1),
        easter - timedelta(days=2),  # Good Friday
        easter + timedelta(days=1),  # Easter Monday
        date(year, 5, 1),
        easter + timedelta(days=39),  # Ascension Day
        easter + timedelta(days=50),  # Whit Monday
        date(year, 10, 3),
        date(year, 12, 25),
        date(year, 12, 26),
    }

    if state_code in {"BW", "BY", "ST"}:
        days.add(date(year, 1, 6))
    if state_code in {"BE", "MV"}:
        days.add(date(year, 3, 8))
    if state_code in {"BW", "BY", "HE", "NW", "RP", "SL"}:
        days.add(easter + timedelta(days=60))  # Corpus Christi
    if state_code == "SL" or (state_code == "BY" and include_assumption_day):
        days.add(date(year, 8, 15))
    if state_code == "TH":
        days.add(date(year, 9, 20))
    if state_code in {"BB", "HB", "HH", "MV", "NI", "SN", "ST", "SH", "TH"}:
        days.add(date(year, 10, 31))
    if state_code in {"BW", "BY", "NW", "RP", "SL"}:
        days.add(date(year, 11, 1))
    if state_code == "SN":
        # Wednesday before November 23
        day = date(year, 11, 22)
        while day.weekday() != 2:
            day -= timedelta(days=1)
        days.add(day)

    return days


def dynamic_factor(day_of_year: pd.Series) -> pd.Series:
    """BDEW dynamic scaling function for H25/P25/S25."""
    t = day_of_year.astype(float)
    factor = (
        -3.92e-10 * t**4
        + 3.20e-7 * t**3
        - 7.02e-5 * t**2
        + 2.10e-3 * t
        + 1.24
    )
    return factor.round(4)


def create_hourly_load_profile(
    csv_path: str | Path,
    profile: str,
    annual_consumption_kwh: float,
    state_code: str,
    year: int = REFERENCE_YEAR,
    include_assumption_day: bool = False,
) -> pd.Series:
    """Create an hourly profile from the BDEW CSV for a specified annual consumption."""
    if pd.Timestamp(year, 12, 31).dayofyear != 365:
        raise ValueError("The reference year must have 365 days in this simplified version.")
    if annual_consumption_kwh <= 0:
        raise ValueError("Annual electricity consumption must be greater than zero.")

    profiles = pd.read_csv(csv_path, sep=";")
    profiles = profiles[profiles["profile"] == profile].copy()
    if profiles.empty:
        raise ValueError(f"Profile {profile} is not present in the CSV.")

    start_time = profiles["interval"].str.slice(0, 5)
    profiles["minute_of_day"] = (
        start_time.str.slice(0, 2).astype(int) * 60
        + start_time.str.slice(3, 5).astype(int)
    )

    lookup = profiles[
        ["month", "day_type", "minute_of_day", "value_kwh_per_1m_kwh"]
    ]

    time_index = pd.date_range(
        f"{year}-01-01",
        f"{year + 1}-01-01",
        freq="15min",
        inclusive="left",
    )
    load = pd.DataFrame({"time": time_index})
    load["month"] = load["time"].dt.month
    load["minute_of_day"] = load["time"].dt.hour * 60 + load["time"].dt.minute
    load["day_of_year"] = load["time"].dt.dayofyear

    holidays = german_holidays(year, state_code, include_assumption_day)
    dates = load["time"].dt.date
    weekday = load["time"].dt.weekday
    load["day_type"] = "WT"
    load.loc[weekday == 5, "day_type"] = "SA"
    load.loc[(weekday == 6) | dates.isin(holidays), "day_type"] = "FT"

    load = load.merge(
        lookup,
        on=["month", "day_type", "minute_of_day"],
        how="left",
        validate="many_to_one",
    )
    if load["value_kwh_per_1m_kwh"].isna().any():
        raise ValueError("The BDEW profile could not be mapped completely.")

    raw = load["value_kwh_per_1m_kwh"].astype(float)
    if profile in DYNAMIC_PROFILES:
        raw = (raw * dynamic_factor(load["day_of_year"])).round(3)

    # After calendar mapping and optional dynamic scaling, normalize to the
    # annual consumption specified by the user.
    quarter_hour_kwh = raw / raw.sum() * annual_consumption_kwh
    hourly = pd.Series(
        quarter_hour_kwh.to_numpy(), index=load["time"], name="load_kwh"
    ).resample("h").sum()

    return hourly.reset_index(drop=True)
