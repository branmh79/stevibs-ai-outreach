from fastapi import APIRouter, Query
from typing import Dict, Any
# Import only the tool that the current pipeline relies on
from tools.family_event_search import FamilyEventSearchTool

router = APIRouter()

@router.get("/events/family")
async def get_family_events(
    location: str = Query(..., description="Location name (e.g. Snellville)"),
    use_mock: bool = Query(False, description="Use mock data for testing"),
    search_radius: int = Query(5000, description="Search radius in meters")
) -> Dict[str, Any]:
    """Family-focused endpoint used by the Streamlit UI."""
    input_data = {
        "location": location,
        "use_mock": use_mock,
        "search_radius": search_radius,
    }

    tool = FamilyEventSearchTool()
    # Use async search for better performance
    result = await tool.search_async(input_data)
    return result
