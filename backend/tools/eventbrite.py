import os
import requests
from datetime import datetime, timedelta

def search_eventbrite_events(location: str, event_type: str):
    token = os.getenv("EVENTBRITE_TOKEN")
    if not token:
        raise ValueError("Missing EVENTBRITE_TOKEN")

    base_url = "https://www.eventbriteapi.com/v3/events/search/"
    headers = {"Authorization": f"Bearer {token}"}

    today = datetime.utcnow()
    in_two_weeks = today + timedelta(days=14)

    params = {
        "location.address": location,
        "q": event_type,
        "start_date.range_start": today.isoformat() + "Z",
        "start_date.range_end": in_two_weeks.isoformat() + "Z",
        "expand": "venue",
        "sort_by": "date"
    }

    res = requests.get(base_url, headers=headers, params=params)
    res.raise_for_status()
    data = res.json()

    results = []
    for event in data.get("events", []):
        results.append({
            "title": event["name"]["text"],
            "description": (event["description"]["text"] or "")[:300],
            "date": event["start"]["local"],
            "website": event["url"],
            "contact_email": None,
            "phone": None
        })

    return results
