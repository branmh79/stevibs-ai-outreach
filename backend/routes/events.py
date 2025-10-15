from fastapi import APIRouter, Query, Depends
from typing import Dict, Any
from workflows.family_event_workflow import family_event_workflow
from models.workflow_state import WorkflowState
from tools.macaronikid_events import MacaroniKIDEventsTool
from auth.dependencies import get_current_user

router = APIRouter()

@router.get("/events/family")
async def get_family_events(
    current_user: dict = Depends(get_current_user),
    use_mock: bool = Query(False, description="Use mock data for testing"),
    search_radius: int = Query(5000, description="Search radius in meters")
) -> Dict[str, Any]:
    """Family-focused endpoint powered by LangGraph workflow. Location is determined by authenticated user."""
    
    # Use the authenticated user's location
    location = current_user["location"]
    
    print(f"[API] Received family events request from user: {current_user['username']}")
    print(f"[API] Location: {location}")
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
    current_user: dict = Depends(get_current_user),
    debug: bool = Query(False, description="Enable debug output")
) -> Dict[str, Any]:
    """MacaroniKID-only endpoint for independent testing. Location is determined by authenticated user."""
    
    # Use the authenticated user's location
    location = current_user["location"]
    
    print(f"[API] Received MacaroniKID events request from user: {current_user['username']}")
    print(f"[API] Location: {location}")
    print(f"[API] Debug mode: {debug}")

    try:
        # Initialize MacaroniKID tool
        macaroni_tool = MacaroniKIDEventsTool()
        
        # Check if location has a configured URL
        location_info = macaroni_tool.location_config.get(location)
        url = location_info["url"] if location_info else None
        
        # Execute MacaroniKID search (using new API approach)
        result = await macaroni_tool.execute_async(location)
        events = result.get('events', [])
        
        # Analyze results - with API, we either get real events or mock events
        real_events = [e for e in events if not e.get('id', '').startswith('mock')]
        mock_events = [e for e in events if e.get('id', '').startswith('mock')]
        
        # Check if location is supported and build appropriate message
        if location_info and (location_info["url"] == "N/A" or not location_info.get("townOwnerId")):
            message = "❌ MacaroniKID not available for this location"
            api_working = False
        elif len(real_events) > 0:
            message = f"🎉 Found {len(real_events)} real events via API!"
            api_working = True
        elif len(mock_events) > 0:
            message = f"⚠️ Returned {len(mock_events)} mock events"
            api_working = False
        else:
            message = "❌ No events found"
            api_working = False

        # Build response
        response = {
            "success": True,
            "location": location,
            "url": url,
            "method": "Direct API Call",
            "total_events": len(events),
            "real_events": len(real_events),
            "mock_events": len(mock_events),
            "api_working": api_working,
            "events": events,
            "source_counts": {"MacaroniKID": len(events)},
            "message": message
        }
        
        if debug:
            response["debug_info"] = {
                "url_configured": url is not None and url != "N/A",
                "url_value": url,
                "available_locations": list(macaroni_tool.location_config.keys()),
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
