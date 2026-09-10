"""Compare PV generation with an hourly standard load profile."""

from __future__ import annotations

import numpy as np


def compare_generation_with_load(
    generation_kwh: np.ndarray,
    load_kwh: np.ndarray,
) -> dict[str, np.ndarray | float]:
    """Calculate direct use, feed-in, and grid import.

    The load profile itself is still created in ``load_profiles.py``. This module
    only performs the simultaneous comparison with PV generation.
    """
    generation = np.asarray(generation_kwh, dtype=float)
    load = np.asarray(load_kwh, dtype=float)
    if generation.shape != load.shape:
        raise ValueError("PV and load time series do not have the same length.")

    direct_use = np.minimum(generation, load)
    feed_in = np.maximum(generation - load, 0.0)
    grid_import = np.maximum(load - generation, 0.0)

    return {
        "direct_use_kwh": direct_use,
        "feed_in_kwh": feed_in,
        "grid_import_kwh": grid_import,
        "generation_sum_kwh": float(generation.sum()),
        "direct_use_sum_kwh": float(direct_use.sum()),
        "feed_in_sum_kwh": float(feed_in.sum()),
        "grid_import_sum_kwh": float(grid_import.sum()),
        "annual_load_kwh": float(load.sum()),
    }
