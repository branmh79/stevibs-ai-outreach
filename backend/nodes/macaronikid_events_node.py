from typing import Dict, Any
from datetime import datetime
from models.workflow_state import WorkflowState
from tools.macaronikid_events import MacaroniKIDEventsTool

def format_macaronikid_datetime(iso_string: str) -> str:
    """Convert ISO datetime string to user-friendly format matching Facebook events."""
    try:
        # Parse the ISO datetime
        dt = datetime.fromisoformat(iso_string.replace('Z', '+00:00'))
        
        # Format to match Facebook event style: "Fri, Sep 5 at 1 PM UTC"
        day_name = dt.strftime('%a')  # Mon, Tue, etc.
        month_day = dt.strftime('%b %-d' if hasattr(dt, 'strftime') else '%b %d')  # Sep 5
        time_str = dt.strftime('%-I %p' if hasattr(dt, 'strftime') else '%I %p').lstrip('0')  # 1 PM
        
        # Handle different OS formatting
        month_day = dt.strftime('%b %d').replace(' 0', ' ')  # Remove leading zero from day
        time_str = dt.strftime('%I %p').lstrip('0')  # Remove leading zero from hour
        
        return f"{day_name}, {month_day} at {time_str} UTC"
    except:
        # Fallback to original string if parsing fails
        return iso_string

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
        print(f"[DEBUG] MacaroniKID node: About to execute for location: {location}")
        result = macaronikid_tool.execute(location)
        print(f"[DEBUG] MacaroniKID node: Result = {result}")
        macaronikid_events = result.get('events', [])
        print(f"[DEBUG] MacaroniKID node: Found {len(macaronikid_events)} events")
        
        # Add MacaroniKID events to the state
        if macaronikid_events:
            # Convert raw dicts from tool into EventData models expected by state
            from models.workflow_state import EventData
            for ev in macaronikid_events:
                # Map MacaroniKID API fields to EventData model
                # Format the datetime to match Facebook event style
                formatted_when = format_macaronikid_datetime(ev.get("startDateTime", ""))
                
                new_event = EventData(
                    title=ev.get("title"),
                    when=formatted_when,  # Use formatted datetime for frontend
                    interested_count=0,  # MacaroniKID doesn't have interested count
                    attending_count=0,  # Set to 0 since MacaroniKID doesn't have attending count
                    website=ev.get("website"),  # Direct website URL
                    description=ev.get("who", "Everyone"),  # Store "who" in description field instead
                    contact_email=None,  # Ignore other data as requested  
                    phone_number=None,   # Ignore other data as requested
                    source="MacaroniKID",
                )
                state.events.append(new_event)
                print(f"[DEBUG] MacaroniKID: Added event '{new_event.title}' with source '{new_event.source}'")
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
    print(f"[DEBUG] MacaroniKID node: About to return patch with {len(state.events)} total events")
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
