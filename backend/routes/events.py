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

    import asyncio
    from functools import partial

    loop = asyncio.get_running_loop()
    final_state = await loop.run_in_executor(None, partial(family_event_workflow.invoke, initial_state, {"recursion_limit": 100}))

    return {
        "success": True,
        "events": [e.dict() for e in final_state.get("events", [])],
        "total_count": len(final_state.get("events", [])),
        "source_counts": final_state.get("source_counts", {}),
        "errors": final_state.get("errors", []),
    }
