import ast
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).parents[1]
MODULE = ROOT / "pv_model" / "pvgis_100case_validation.py"


def _module_ast():
    return ast.parse(MODULE.read_text(encoding="utf-8"))


def test_default_benchmark_is_defined_as_10_by_10_matrix():
    tree = _module_ast()
    assignments = {
        node.targets[0].id: node.value
        for node in tree.body
        if isinstance(node, ast.Assign)
        and len(node.targets) == 1
        and isinstance(node.targets[0], ast.Name)
    }
    locations = ast.literal_eval(assignments["LOCATIONS"])
    configurations = ast.literal_eval(assignments["CONFIGURATIONS"])
    assert len(locations) == 10
    assert len(configurations) == 10
    assert len(locations) * len(configurations) == 100


def test_global_poa_is_not_an_error_driver_parameter():
    source = MODULE.read_text(encoding="utf-8")
    marker = 'drivers = error_driver_statistics('
    start = source.index(marker)
    end = source.index('    return results, stats, drivers', start)
    driver_block = source[start:end]
    assert '"pvgis_global_poa_kwh_m2_a"' not in driver_block
    for expected in [
        '"latitude"',
        '"longitude"',
        '"tilt_deg"',
        '"azimuth_deviation_south_deg"',
        '"peak_power_kwp"',
    ]:
        assert expected in driver_block
