import os
from typing import Dict, Any
from googleapiclient.discovery import build
from .base_tool import BaseTool

class GoogleSearchTool(BaseTool):
    """
    Tool for searching events using Google Custom Search API.
    Input: {"location": str, "event_type": str, "num_results": int (optional, default=5)}
    Output: {"success": bool, "events": list, "count": int, "error": str (if any)}
    """

    def __call__(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        try:
            self.validate_input(input_data)
            
            location = input_data["location"]
            event_type = input_data["event_type"]
            num_results = input_data.get("num_results", 5)
            
            events = self._search_events(location, event_type, num_results)
            
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
        
        # Validate num_results if provided
        if "num_results" in input_data:
            num_results = input_data["num_results"]
            if not isinstance(num_results, int) or num_results < 1 or num_results > 10:
                raise ValueError("num_results must be an integer between 1 and 10")

    def _search_events(self, location: str, event_type: str, num_results: int = 5) -> list:
        """Internal method to search Google for events."""
        api_key = os.getenv("GOOGLE_CSE_API_KEY")
        cse_id = os.getenv("GOOGLE_CSE_ID")

        if not api_key:
            raise ValueError("Missing GOOGLE_CSE_API_KEY")
        if not cse_id:
            raise ValueError("Missing GOOGLE_CSE_ID")

        service = build("customsearch", "v1", developerKey=api_key)

        query = f"{event_type} events near {location}"
        results = service.cse().list(q=query, cx=cse_id, num=num_results).execute()

        events = []
        for item in results.get("items", []):
            events.append({
                "title": item.get("title"),
                "description": item.get("snippet", "")[:300],
                "date": None,  # Google search doesn't provide dates
                "website": item.get("link"),
                "contact_email": None,
                "phone_number": None
            })

        return events

# Convenience function for backward compatibility
def search_google_events(location: str, event_type: str):
    """Legacy function - use GoogleSearchTool() instead."""
    tool = GoogleSearchTool()
    result = tool({"location": location, "event_type": event_type})
    if result["success"]:
        return result["events"]
    else:
        raise ValueError(result["error"])
