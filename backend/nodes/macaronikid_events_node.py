from typing import Dict, Any
from models.workflow_state import WorkflowState
from tools.macaronikid_events import MacaroniKIDEventsTool

def macaronikid_events_node(state: WorkflowState) -> dict:
    """Node for fetching MacaroniKID events using web scraping."""
    
    try:
        # Initialize MacaroniKID events tool
        macaronikid_tool = MacaroniKIDEventsTool()
        
        # Get search parameters from state
        location = state.location
        # Note: start_date and end_date are not currently supported in the workflow state
        start_date = None
        end_date = None
        
        # Execute MacaroniKID events search
        result = macaronikid_tool.execute(location)
        macaronikid_events = result.get('events', [])
        
        # Add MacaroniKID events to the state
        if macaronikid_events:
            # Convert raw dicts from tool into EventData models expected by state
            from models.workflow_state import EventData
            for ev in macaronikid_events:
                # Map MacaroniKID API fields to EventData model
                state.events.append(
                    EventData(
                        title=ev.get("title"),
                        when=ev.get("startDateTime"),  # Use full startDateTime for frontend
                        interested_count=0,  # MacaroniKID doesn't have interested count
                        attending_count=ev.get("who", "Everyone"),  # Use "who" instead of attending count
                        website=ev.get("website"),  # Direct website URL
                        description=None,  # Ignore other data as requested
                        contact_email=None,  # Ignore other data as requested  
                        phone_number=None,   # Ignore other data as requested
                        source="MacaroniKID",
                    )
                )
            state.message = f"Found {len(macaronikid_events)} MacaroniKID events"
        else:
            # Check if location is supported
            macaronikid_tool = MacaroniKIDEventsTool()
            location_info = macaronikid_tool.location_config.get(location)
            if location_info and (location_info["url"] == "N/A" or not location_info["townOwnerId"]):
                state.message = "MacaroniKID not available for this location"
            else:
                state.message = "No MacaroniKID events found"
        
        # Update source counts
        if "MacaroniKID" not in state.source_counts:
            state.source_counts["MacaroniKID"] = 0
        state.source_counts["MacaroniKID"] += len(macaronikid_events)
        
        # Mark workflow as complete since this is the last node
        state.is_complete = True
        
    except Exception as e:
        state.error = f"Error fetching MacaroniKID events: {str(e)}"
        state.errors.append(f"MacaroniKID error: {str(e)}")
    
    # Return only the fields that changed (LangGraph requirement)
    patch = {}
    if state.events:
        patch["events"] = state.events
    if state.message:
        patch["message"] = state.message
    if state.error:
        patch["error"] = state.error
    if state.source_counts:
        patch["source_counts"] = state.source_counts
    if state.errors:
        patch["errors"] = state.errors
    if state.is_complete:
        patch["is_complete"] = True
    
    return patch
