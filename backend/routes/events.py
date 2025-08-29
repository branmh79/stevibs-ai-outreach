from fastapi import APIRouter, Query
from typing import Dict, Any
from workflows.family_event_workflow import family_event_workflow
from models.workflow_state import WorkflowState

router = APIRouter()

@router.get("/events/family")
async def get_family_events(
    location: str = Query(..., description="Location name (e.g. Snellville)"),
    use_mock: bool = Query(False, description="Use mock data for testing"),
    search_radius: int = Query(5000, description="Search radius in meters")
) -> Dict[str, Any]:
    """Family-focused endpoint powered by LangGraph workflow."""
    
    print(f"[API] Received family events request for location: {location}")
    print(f"[API] Parameters - use_mock: {use_mock}, search_radius: {search_radius}")

    # Build initial state and run LangGraph workflow synchronously (can wrap in executor for async)
    initial_state = {
        "location": location,
        "use_mock": use_mock,
        "search_radius": search_radius,
        "events": [],
        "source_counts": {},
        "errors": [],
        "is_complete": False,
    }

    # Invoke workflow directly (now async-native)
    final_state = await family_event_workflow.ainvoke(initial_state, {"recursion_limit": 100})

    return {
        "success": True,
        "events": final_state.get("events", []),
        "total_count": len(final_state.get("events", [])),
        "source_counts": final_state.get("source_counts", {}),
        "errors": final_state.get("errors", []),
    }
