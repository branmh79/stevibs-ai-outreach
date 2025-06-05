from fastapi import APIRouter, Query
from utils.geocode import geocode_address
from data.locations import LOCATION_ADDRESSES
from scripts.scrape_events import scrape_real_events
from data.cache import SCRAPED_PLACE_CACHE
from scripts.scrape_events import format_events_for_output

router = APIRouter()

@router.get("/events")
def get_events(
    location: str = Query(..., description="Location name (e.g. Snellville)"),
    event_type: str = Query("Summer Camp", description="Type of event to search for")
):
    if location not in LOCATION_ADDRESSES:
        return {"error": f"Unknown location '{location}'."}

    address = LOCATION_ADDRESSES[location]
    coords = geocode_address(address)
    places = scrape_real_events(coords["lat"], coords["lon"], query=event_type)
    SCRAPED_PLACE_CACHE[location] = places

    return format_events_for_output(location, places)
