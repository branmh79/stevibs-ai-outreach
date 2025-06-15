import os
import requests
from datetime import datetime, timedelta
from dateutil.parser import isoparse
from data.locations import LOCATION_ADDRESSES

GEOCODE_URL = "https://nominatim.openstreetmap.org/search"

def geocode_address(address: str):
    response = requests.get(GEOCODE_URL, params={
        "q": address,
        "format": "json",
        "limit": 1
    }, headers={"User-Agent": "stevibs-ai-outreach/1.0"})
    response.raise_for_status()
    data = response.json()
    if not data:
        raise ValueError(f"Geocoding failed for address: {address}")
    return float(data[0]["lat"]), float(data[0]["lon"])

def search_ticketmaster_events(location: str, event_type: str, start_date: str = None, end_date: str = None):
    api_key = os.getenv("TICKETMASTER_API_KEY")
    if not api_key:
        raise ValueError("Missing TICKETMASTER_API_KEY")

    # Get address from location label
    address = LOCATION_ADDRESSES.get(location)
    if not address:
        raise ValueError(f"No address found for location: {location}")

    # Geocode address to lat/lon
    lat, lon = geocode_address(address)

    # Format dates for Ticketmaster API
    start = isoparse(start_date) if start_date else datetime.utcnow()
    end = isoparse(end_date) if end_date else start + timedelta(days=30)
    start_iso = start.strftime("%Y-%m-%dT%H:%M:%SZ")
    end_iso = end.strftime("%Y-%m-%dT%H:%M:%SZ")

    url = "https://app.ticketmaster.com/discovery/v2/events.json"
    params = {
        "apikey": api_key,
        "keyword": event_type,
        "latlong": f"{lat},{lon}",
        "radius": "25",
        "unit": "miles",
        "startDateTime": start_iso,
        "endDateTime": end_iso,
        "size": 10,
        "sort": "date,asc"
    }

    print("TICKETMASTER REQUEST PARAMS:", params)

    response = requests.get(url, params=params)
    response.raise_for_status()
    data = response.json()

    events = []
    for event in data.get('_embedded', {}).get('events', []):
        events.append({
            "title": event.get("name"),
            "date": event.get("dates", {}).get("start", {}).get("localDate"),
            "description": event.get("info", "")[:300],
            "website": event.get("url"),
            "contact_email": None,
            "phone": None
        })

    return events
