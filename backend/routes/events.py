from fastapi import APIRouter, Query
from typing import Dict, Any
from workflows.family_event_workflow import family_event_workflow
from models.workflow_state import WorkflowState
from tools.macaronikid_events import MacaroniKIDEventsTool

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

@router.get("/events/macaronikid")
async def get_macaronikid_events(
    location: str = Query(..., description="Location name (e.g. Snellville, GA)"),
    debug: bool = Query(False, description="Enable debug output")
) -> Dict[str, Any]:
    """MacaroniKID-only endpoint for independent testing."""
    
    print(f"[API] Received MacaroniKID events request for location: {location}")
    print(f"[API] Debug mode: {debug}")

    try:
        # Initialize MacaroniKID tool
        macaroni_tool = MacaroniKIDEventsTool()
        
        # Check if location has a configured URL
        url = macaroni_tool.location_urls.get(location)
        
        # Execute MacaroniKID search (using new API approach)
        result = await macaroni_tool.execute_async(location)
        events = result.get('events', [])
        
        # Analyze results - with API, we either get real events or mock events
        real_events = [e for e in events if not e.get('event_id', '').startswith('mock')]
        mock_events = [e for e in events if e.get('event_id', '').startswith('mock')]
        
        # Build response
        response = {
            "success": True,
            "location": location,
            "url": url,
            "method": "Network Interception",
            "total_events": len(events),
            "real_events": len(real_events),
            "mock_events": len(mock_events),
            "network_interception_working": len(real_events) > 0,
            "events": events,
            "source_counts": {"MacaroniKID": len(events)},
            "message": f"🎉 Found {len(real_events)} real events via network interception!" if len(real_events) > 0 else 
                      f"⚠️ Returned {len(mock_events)} mock events" if len(mock_events) > 0 else 
                      "❌ No events found"
        }
        
        if debug:
            response["debug_info"] = {
                "url_configured": url is not None and url != "N/A",
                "url_value": url,
                "available_locations": list(macaroni_tool.location_urls.keys()),
                "sample_event": events[0] if events else None
            }
        
        return response
        
    except Exception as e:
        print(f"[ERROR] MacaroniKID endpoint error: {e}")
        return {
            "success": False,
            "location": location,
            "error": str(e),
            "message": "❌ MacaroniKID request failed"
        }
