from typing import Dict, Any, List
from .base_tool import BaseTool
from .contact_scraper import ContactScraperTool

class UnifiedEventSearchTool(BaseTool):
    """
    Unified tool that focuses on web scraping for local events.
    Input: {
        "location": str,
        "event_type": str,
        "use_mock": bool (optional, default=False),
        "search_radius": int (optional, default=5000) - meters
    }
    Output: {
        "success": bool,
        "events": list,
        "total_count": int,
        "source_counts": dict,
        "errors": list
    }
    """

    def __init__(self):
        self.tools = {
            "scraper": ContactScraperTool()
        }

    def __call__(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        try:
            self.validate_input(input_data)
            
            location = input_data["location"]
            event_type = input_data["event_type"]
            use_mock = input_data.get("use_mock", False)
            search_radius = input_data.get("search_radius", 5000)
            
            all_events = []
            source_counts = {}
            errors = []
            
            # Focus on web scraping
            try:
                tool = self.tools["scraper"]
                
                tool_input = {
                    "location": location,
                    "query": event_type,
                    "use_mock": use_mock,
                    "search_radius": search_radius
                }
                
                result = tool(tool_input)
                
                if result["success"]:
                    # Convert Place objects to event format
                    events = []
                    for place in result["places"]:
                        events.append({
                            "title": place.get("name"),
                            "description": place.get("description"),
                            "date": None,  # Will be enhanced later
                            "website": place.get("website"),
                            "contact_email": place.get("contact_email"),
                            "phone": place.get("phone_number"),
                            "address": place.get("address"),
                            "source": "web_scraper"
                        })
                    
                    all_events.extend(events)
                    source_counts["web_scraper"] = len(events)
                else:
                    errors.append(f"scraper: {result.get('error', 'Unknown error')}")
                    source_counts["web_scraper"] = 0
                    
            except Exception as e:
                errors.append(f"scraper: {str(e)}")
                source_counts["web_scraper"] = 0
            
            return {
                "success": True,
                "events": all_events,
                "total_count": len(all_events),
                "source_counts": source_counts,
                "errors": errors
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

# Global instance for easy access
unified_search = UnifiedEventSearchTool()

# Convenience functions
def search_events(location: str, event_type: str, **kwargs):
    """Search for events using web scraping."""
    return unified_search.search_events(location, event_type, **kwargs) 