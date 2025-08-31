from typing import Dict, Any
from datetime import datetime
from models.workflow_state import WorkflowState
from tools.schools import SchoolsTool

def schools_node(state: WorkflowState) -> dict:
    """Node for fetching school events using web scraping."""
    
    try:
        # Initialize Schools events tool
        schools_tool = SchoolsTool()
        
        # Get search parameters from state
        location = state.location
        # Note: start_date and end_date are not currently supported in the workflow state
        start_date = None
        end_date = None
        
        # Execute Schools events search
        print(f"[DEBUG] Schools node: About to execute for location: {location}")
        result = schools_tool.execute(location, start_date, end_date)
        print(f"[DEBUG] Schools node: Result = {result}")
        school_events = result.get('events', [])
        print(f"[DEBUG] Schools node: Found {len(school_events)} events")
        
        # Add Schools events to the state
        if school_events:
            # Convert raw dicts from tool into EventData models expected by state
            from models.workflow_state import EventData
            for ev in school_events:
                new_event = EventData(
                    title=ev.get("title"),
                    when=ev.get("when"),  # Use formatted datetime for frontend
                    address=ev.get("address"),  # School name for display
                    interested_count=ev.get("interested_count", 0),  # Schools don't have interested count
                    attending_count=ev.get("attending_count", 0),   # Schools don't have attending count
                    website=ev.get("website"),  # Direct website URL
                    description=ev.get("description", ""),
                    contact_email=ev.get("contact_email"),
                    phone_number=ev.get("phone_number"),
                    source=ev.get("source", "Schools"),
                )
                state.events.append(new_event)
                print(f"[DEBUG] Schools: Added event '{new_event.title}' with source '{new_event.source}'")
            state.message = f"Found {len(school_events)} school events"
        else:
            # Check if location has school configuration
            school_config = schools_tool.location_config.get(location, {})
            if not school_config or not any(urls for urls in school_config.values()):
                state.message = "No school URLs configured for this location"
            else:
                state.message = "No school events found"
        
        # Update source counts
        if "Schools" not in state.source_counts:
            state.source_counts["Schools"] = 0
        state.source_counts["Schools"] += len(school_events)
        
        # Mark workflow as complete since this is the last node
        state.is_complete = True
        
    except Exception as e:
        state.error = f"Error fetching school events: {str(e)}"
        state.errors.append(f"Schools error: {str(e)}")
    
    # Return only the fields that changed (LangGraph requirement)
    print(f"[DEBUG] Schools node: About to return patch with {len(state.events)} total events")
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
