import os
import requests
from datetime import datetime, timedelta
from typing import Dict, Any
from .base_tool import BaseTool

class EventbriteTool(BaseTool):
    """
    Tool for searching events on Eventbrite.
    Input: {"location": str, "event_type": str}
    Output: {"success": bool, "events": list, "error": str (if any)}
    """

    def __call__(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        try:
            self.validate_input(input_data)
            
            location = input_data["location"]
            event_type = input_data["event_type"]
            
            events = self._search_events(location, event_type)
            
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

    def _search_events(self, location: str, event_type: str) -> list:
        """Internal method to search Eventbrite events."""
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

# Convenience function for backward compatibility
def search_eventbrite_events(location: str, event_type: str):
    """Legacy function - use EventbriteTool() instead."""
    tool = EventbriteTool()
    result = tool({"location": location, "event_type": event_type})
    if result["success"]:
        return result["events"]
    else:
        raise ValueError(result["error"])
