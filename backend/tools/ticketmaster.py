import os
import requests
from datetime import datetime, timedelta
from dateutil.parser import isoparse
from typing import Dict, Any
from .base_tool import BaseTool
from data.locations import LOCATION_ADDRESSES

GEOCODE_URL = "https://nominatim.openstreetmap.org/search"

class TicketmasterTool(BaseTool):
    """
    Tool for searching events on Ticketmaster.
    Input: {"location": str, "event_type": str, "start_date": str (optional), "end_date": str (optional)}
    Output: {"success": bool, "events": list, "count": int, "error": str (if any)}
    """

    def __call__(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        try:
            self.validate_input(input_data)
            
            location = input_data["location"]
            event_type = input_data["event_type"]
            start_date = input_data.get("start_date")
            end_date = input_data.get("end_date")
            
            events = self._search_events(location, event_type, start_date, end_date)
            
            return {
                "success": True,
                "events": events,
                "count": len(events)
            }
            
        except Exception as e:
            return self.handle_error(e)

    def validate_input(self, input_data: Dict[str, Any]) -> None:
        """Validate required input parameters."""
        required_fields = ["location", "event_type"]
        for field in required_fields:
            if field not in input_data:
                raise ValueError(f"Missing required field: {field}")
            if not input_data[field] or not isinstance(input_data[field], str):
                raise ValueError(f"Field {field} must be a non-empty string")

    def _geocode_address(self, address: str) -> tuple:
        """Geocode an address to lat/lon coordinates."""
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

    def _search_events(self, location: str, event_type: str, start_date: str | None = None, end_date: str | None = None) -> list:
        """Internal method to search Ticketmaster events."""
        api_key = os.getenv("TICKETMASTER_API_KEY")
        if not api_key:
            raise ValueError("Missing TICKETMASTER_API_KEY")

        # Get address from location label
        address = LOCATION_ADDRESSES.get(location)
        if not address:
            raise ValueError(f"No address found for location: {location}")

        # Geocode address to lat/lon
        lat, lon = self._geocode_address(address)

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
                "phone": None  # Ticketmaster doesn't provide phone numbers
            })

        return events

# Convenience function for backward compatibility
def search_ticketmaster_events(location: str, event_type: str, start_date: str | None = None, end_date: str | None = None):
    """Legacy function - use TicketmasterTool() instead."""
    tool = TicketmasterTool()
    input_data = {"location": location, "event_type": event_type}
    if start_date:
        input_data["start_date"] = start_date
    if end_date:
        input_data["end_date"] = end_date
    
    result = tool(input_data)
    if result["success"]:
        return result["events"]
    else:
        raise ValueError(result["error"])

# Keep the old geocode function for backward compatibility
def geocode_address(address: str):
    """Legacy function - use TicketmasterTool()._geocode_address() instead."""
    tool = TicketmasterTool()
    return tool._geocode_address(address)
