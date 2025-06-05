# backend/utils/geocode.py

import requests

def geocode_address(address: str) -> dict:
    url = "https://nominatim.openstreetmap.org/search"
    params = {"q": address, "format": "json"}
    headers = {"User-Agent": "stevibs-ai-outreach/1.0"}

    response = requests.get(url, params=params, headers=headers)
    response.raise_for_status()

    results = response.json()
    if not results:
        raise ValueError(f"Could not geocode address: {address}")

    return {
        "lat": float(results[0]["lat"]),
        "lon": float(results[0]["lon"]),
    }
