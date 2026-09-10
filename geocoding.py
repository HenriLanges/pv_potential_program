"""Simple location lookup from an address or coordinates."""

from __future__ import annotations

from geopy.exc import GeocoderServiceError, GeocoderTimedOut
from geopy.geocoders import Nominatim


def geocode_address(address: str) -> tuple[str, float, float]:
    """Resolve display name, latitude, and longitude from an address."""
    if not address.strip():
        raise ValueError("Please enter an address or place.")

    geolocator = Nominatim(user_agent="pv-potential-bdew/1.0")
    try:
        location = geolocator.geocode(address, exactly_one=True, timeout=20)
    except (GeocoderServiceError, GeocoderTimedOut) as exc:
        raise RuntimeError(
            "The geocoding service is currently unavailable. "
            "Alternatively, enter the coordinates manually."
        ) from exc

    if location is None:
        raise ValueError(
            "The location could not be found. Please provide a more specific address "
            "or enter the coordinates manually."
        )

    return location.address, float(location.latitude), float(location.longitude)


def timezone_for_coordinates(latitude: float, longitude: float) -> str:
    """Return the time basis used by the German BDEW model.

    The parameters remain part of the function so the location logic stays clear
    and can be extended easily later. Because the BDEW load profiles used here
    apply to Germany, Europe/Berlin is intentionally used.
    """
    _ = latitude, longitude
    return "Europe/Berlin"
