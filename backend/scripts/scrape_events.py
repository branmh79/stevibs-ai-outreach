import sys
import os
import json
from typing import List

# Add project root to sys.path for absolute imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from backend.data.locations import LOCATION_ADDRESSES
from backend.utils.geocode import geocode_address
from backend.models.place import Place
from backend.data.cache import SCRAPED_PLACE_CACHE

def mock_scrape_nearby(lat: float, lon: float) -> List[Place]:
    # Return mock data — this simulates real scraping output
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
    # Validate and return Pydantic models
    return [Place(**entry) for entry in mock_results]

def main(location_name: str):
    address = LOCATION_ADDRESSES.get(location_name)
    if not address:
        raise ValueError(f"Location '{location_name}' not found in LOCATION_ADDRESSES.")

    coords = geocode_address(address)
    print(f"\n📍 {location_name} → {address}")
    print(f"🧭 Coordinates: {coords['lat']}, {coords['lon']}\n")

    places = mock_scrape_nearby(coords["lat"], coords["lon"])
    SCRAPED_PLACE_CACHE[location_name] = places  # Store temporarily in memory

    print(json.dumps([p.model_dump(mode="json") for p in places], indent=2))



if __name__ == "__main__":
    location = sys.argv[1] if len(sys.argv) > 1 else "Snellville"
    main(location)
