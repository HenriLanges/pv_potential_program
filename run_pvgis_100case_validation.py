"""CLI runner for the reproducible 100-case PVGIS validation."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

from pv_model.pvgis_100case_validation import default_100_cases, run_100_case_validation, validate_case_table
from pv_model.validation_plots import bland_altman_figure, error_distribution_figure, error_driver_figure, regression_figure


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--cases-csv", type=Path, default=None)
    parser.add_argument("--start-year", type=int, default=2014)
    parser.add_argument("--end-year", type=int, default=2023)
    parser.add_argument("--output", type=Path, default=Path("pvgis_100case_results"))
    parser.add_argument("--efficiency", type=float, default=0.20)
    parser.add_argument("--temp-coeff", type=float, default=-0.004)
    parser.add_argument("--system-loss-pct", type=float, default=14.0)
    args = parser.parse_args()

    cases = default_100_cases() if args.cases_csv is None else validate_case_table(pd.read_csv(args.cases_csv), require_100=True)
    args.output.mkdir(parents=True, exist_ok=True)
    plot_dir = args.output / "plots"
    plot_dir.mkdir(exist_ok=True)

    def progress(done, total, message):
        print(f"[{done:3d}/{total}] {message}", flush=True)

    results, stats, drivers = run_100_case_validation(
        cases=cases,
        start_year=args.start_year,
        end_year=args.end_year,
        efficiency_25=args.efficiency,
        temperature_coefficient_per_k=args.temp_coeff,
        system_loss_pct=args.system_loss_pct,
        progress_callback=progress,
    )
    results.to_csv(args.output / "pvgis_100case_results.csv", index=False)
    drivers.to_csv(args.output / "pvgis_error_driver_correlations.csv", index=False)
    (args.output / "pvgis_validation_statistics.json").write_text(json.dumps(stats, indent=2), encoding="utf-8")
    cases.to_csv(args.output / "benchmark_cases.csv", index=False)

    figures = {
        "energy_model_vs_pvgis.png": regression_figure(results, "pvgis_energy_kwh_a", "model_energy_kwh_a", "PVGIS energy [kWh/a]", "Model energy [kWh/a]", "Annual PV energy: model vs PVGIS"),
        "energy_bland_altman.png": bland_altman_figure(results),
        "specific_yield_model_vs_pvgis.png": regression_figure(results, "pvgis_specific_yield_kwh_kwp_a", "model_specific_yield_kwh_kwp_a", "PVGIS specific yield [kWh/kWp·a]", "Model specific yield [kWh/kWp·a]", "Specific PV yield: model vs PVGIS"),
        "energy_error_distribution.png": error_distribution_figure(results),
        "direct_poa_model_vs_pvgis.png": regression_figure(results, "pvgis_direct_poa_kwh_m2_a", "model_direct_poa_kwh_m2_a", "PVGIS direct POA [kWh/m²·a]", "Model direct POA [kWh/m²·a]", "Direct in-plane irradiation"),
        "global_poa_model_vs_pvgis.png": regression_figure(results, "pvgis_global_poa_kwh_m2_a", "model_global_poa_kwh_m2_a", "PVGIS global POA [kWh/m²·a]", "Model global POA [kWh/m²·a]", "Global in-plane irradiation"),
    }
    driver_labels = {
        "latitude": "Latitude [°]",
        "longitude": "Longitude [°]",
        "tilt_deg": "Module tilt [°]",
        "azimuth_deviation_south_deg": "Azimuth deviation from south [°]",
        "peak_power_kwp": "Nominal power [kWp]",
    }
    for col, label in driver_labels.items():
        figures[f"energy_error_vs_{col}.png"] = error_driver_figure(results, col, "energy_error_pct", label, "Relative energy error [%]", f"Relative energy error vs {label}")
    for filename, fig in figures.items():
        fig.savefig(plot_dir / filename, dpi=300, bbox_inches="tight")
        plt.close(fig)
    print(f"Saved results to {args.output.resolve()}")


if __name__ == "__main__":
    main()
