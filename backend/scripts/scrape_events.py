import sys
import os
import json
import requests
from bs4 import BeautifulSoup
from models.place import Place
from typing import List, Dict
import re

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

def scrape_real_events(lat: float, lon: float, query: str = "Summer Camp") -> List[Place]:
    import os

    api_key = os.getenv("GOOGLE_PLACES_API_KEY")
    radius = 5000  # meters

    search_url = (
        "https://maps.googleapis.com/maps/api/place/textsearch/json"
    )
    details_url = (
        "https://maps.googleapis.com/maps/api/place/details/json"
    )

    search_params = {
        "query": query,
        "location": f"{lat},{lon}",
        "radius": radius,
        "key": api_key
    }

    res = requests.get(search_url, params=search_params)
    data = res.json()

    results = []

    def extract_email_from_website(url):
        try:
            response = requests.get(url, timeout=5)
            soup = BeautifulSoup(response.text, "html.parser")
            emails = re.findall(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", soup.text)
            return emails[0] if emails else None
        except:
            return None
        
    

    for result in data.get("results", [])[:5]:
        place_id = result.get("place_id")
        details_params = {
            "place_id": place_id,
            "fields": "name,website,formatted_address,types,editorial_summary,formatted_phone_number",
            "key": api_key
        }
        details_res = requests.get(details_url, params=details_params)
        details = details_res.json().get("result", {})

        website = details.get("website")
        email = extract_email_from_website(website) if website else None
        phone_number = details.get("formatted_phone_number")
        editorial = details.get("editorial_summary", {})
        overview = editorial.get("overview")
        description = overview or details.get("types", ["No description"])[0].replace("_", " ").title()


        results.append(Place(
            name=details.get("name", "Unnamed Event"),
            description=description,
            address=details.get("formatted_address", "Unknown address"),
            website=website,
            contact_email=email,
            phone_number=phone_number
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
            "contact_email": place.contact_email,
            "phone_number": place.phone_number
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
