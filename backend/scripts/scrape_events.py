import sys
import os
import json
import requests
from bs4 import BeautifulSoup
from models.place import Place
from typing import List, Dict

# Fix for CLI execution (keep this for running manually)
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from data.locations import LOCATION_ADDRESSES
from utils.geocode import geocode_address
from models.place import Place
from data.cache import SCRAPED_PLACE_CACHE

def mock_scrape_nearby(lat: float, lon: float) -> List[Place]:
    mock_results = [
        {
            "name": "Camp Sunshine Summer Program",
            "description": "Weekly day camp for ages 6–12 focused on outdoor activities.",
            "address": "200 Camp Sunshine Rd, Snellville, GA",
            "website": "https://campsunshine.org",
            "contact_email": "hello@campsunshine.org"
        },
        {
            "name": "Snellville Sports & Rec Meetup",
            "description": "Weekly evening sports meetup for local families.",
            "address": "500 Rec Center Dr, Snellville, GA",
            "website": "https://snellvillerec.org",
            "contact_email": "info@snellvillerec.org"
        },
        {
            "name": "Creative Minds Art Camp",
            "description": "Kids art camp for ages 5–10 focused on creativity and crafts.",
            "address": "300 Art Blvd, Snellville, GA",
            "website": "https://creativemindsart.com",
            "contact_email": "camp@creativemindsart.com"
        }
    ]
    return [Place(**entry) for entry in mock_results]

def scrape_real_events(lat: float, lon: float) -> List[Place]:
    import os

    api_key = os.getenv("GOOGLE_PLACES_API_KEY")
    radius = 5000  # meters
    query = "summer camp"

    url = (
        "https://maps.googleapis.com/maps/api/place/textsearch/json?"
        f"query={requests.utils.quote(query)}"
        f"&location={lat},{lon}&radius={radius}&key={api_key}"
    )

    res = requests.get(url)
    data = res.json()

    results = []
    for result in data.get("results", [])[:5]:
        results.append(Place(
            name=result.get("name", "Unnamed Event"),
            description=result.get("types", ["No description"])[0],
            address=result.get("formatted_address", "Unknown address"),
            website=None,  # You'd need a Place Details call for website
            contact_email=None  # Not provided in Places API
        ))

    return results


def format_events_for_output(location_name: str, places: List[Place]) -> List[Dict]:
    return [
        {
            "location_name": location_name,
            "stevi_b_address": LOCATION_ADDRESSES[location_name],
            "event_name": place.name,
            "description": place.description,
            "event_address": place.address,
            "website": str(place.website) if place.website else None,
            "contact_email": place.contact_email
        }
        for place in places
    ]

def main(location_name: str):
    address = LOCATION_ADDRESSES.get(location_name)
    if not address:
        raise ValueError(f"Location '{location_name}' not found in LOCATION_ADDRESSES.")

    coords = geocode_address(address)
    print(f"\n📍 {location_name} → {address}")
    print(f"🧭 Coordinates: {coords['lat']}, {coords['lon']}\n")

    places = mock_scrape_nearby(coords["lat"], coords["lon"])
    SCRAPED_PLACE_CACHE[location_name] = places
    formatted = format_events_for_output(location_name, places)
    print(json.dumps(formatted, indent=2))

if __name__ == "__main__":
    location = sys.argv[1] if len(sys.argv) > 1 else "Snellville"
    main(location)
