"""Monetary valuation of directly used and exported PV electricity."""

from __future__ import annotations


def calculate_annual_economic_value(
    direct_use_kwh: float,
    feed_in_kwh: float,
    electricity_price_eur_per_kwh: float,
    feed_in_tariff_eur_per_kwh: float,
) -> dict[str, float]:
    """Calculate annual gross value excluding investment costs."""
    if electricity_price_eur_per_kwh < 0.0 or feed_in_tariff_eur_per_kwh < 0.0:
        raise ValueError("Electricity price and feed-in tariff must not be negative.")

    avoided_purchase_cost = (
        float(direct_use_kwh) * float(electricity_price_eur_per_kwh)
    )
    feed_in_revenue = float(feed_in_kwh) * float(feed_in_tariff_eur_per_kwh)
    return {
        "avoided_purchase_cost_eur": avoided_purchase_cost,
        "feed_in_revenue_eur": feed_in_revenue,
        "total_value_eur": avoided_purchase_cost + feed_in_revenue,
    }
