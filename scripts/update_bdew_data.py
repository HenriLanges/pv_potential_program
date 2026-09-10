"""Download the official BDEW XLSX file and rebuild the project CSV."""

from __future__ import annotations

import argparse
from io import BytesIO
from pathlib import Path

import pandas as pd
import requests

DEFAULT_URL = (
    "https://www.bdew.de/media/documents/"
    "Kopie_von_Repr%C3%A4sentative_Profile_BDEW_H25_G25_L25_P25_S25_"
    "Ver%C3%B6ffentlichung.xlsx"
)
PROFILES = ["H25", "G25", "L25", "P25", "S25"]


def update(url: str, output: Path) -> None:
    response = requests.get(url, timeout=120)
    response.raise_for_status()
    workbook = BytesIO(response.content)

    records = []
    for profile in PROFILES:
        sheet = pd.read_excel(workbook, sheet_name=profile, header=None)
        day_types = sheet.iloc[3, 2:38].tolist()
        intervals = sheet.iloc[4:100, 1].tolist()

        if len(day_types) != 36 or len(intervals) != 96:
            raise ValueError(f"Unexpected table layout in sheet {profile}.")

        for column_offset, day_type in enumerate(day_types):
            month = column_offset // 3 + 1
            values = sheet.iloc[4:100, column_offset + 2].tolist()
            for interval, value in zip(intervals, values, strict=True):
                records.append(
                    {
                        "profile": profile,
                        "month": month,
                        "day_type": day_type,
                        "interval": interval,
                        "value_kwh_per_1m_kwh": value,
                    }
                )

        workbook.seek(0)

    output.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(records).to_csv(output, sep=";", index=False)
    print(f"{len(records)} rows written: {output}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default=DEFAULT_URL)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(__file__).parents[1]
        / "data"
        / "bdew_standard_load_profiles_2025.csv",
    )
    args = parser.parse_args()
    update(args.url, args.output)
