from typing import Dict, Any
from models.workflow_state import WorkflowState
from tools.facebook_events import FacebookEventsTool
import os

def facebook_events_node(state: WorkflowState) -> dict:
    """Node for fetching Facebook events using web scraping."""
    
    try:
        # Initialize Facebook events tool (no credentials needed for web scraping)
        facebook_tool = FacebookEventsTool()
        
        # Get search parameters from state
        location = state.location
        # Note: start_date and end_date are not currently supported in the workflow state
        start_date = None
        end_date = None
        
        # Execute Facebook events search
        facebook_events = facebook_tool.execute(location, start_date, end_date)

        # Debug: print the exact URL that was used for the search so we can replicate it manually
        if getattr(facebook_tool, "last_url", None):
            print(f"[DEBUG] Facebook search URL: {facebook_tool.last_url}")
        
        # Add Facebook events to the state
        if facebook_events:
            # Convert raw dicts from tool into EventData models expected by state
            from models.workflow_state import EventData
            for ev in facebook_events:
                state.events.append(
                    EventData(
                        title=ev.get("title"),
                        when=ev.get("when"),
                        interested_count=ev.get("interested_count"),
                        attending_count=ev.get("attending_count"),
                        website=ev.get("website"),
                        description=ev.get("description"),
                        source=ev.get("source", "Facebook (JSON)"),
                    )
                )
            state.message = f"Found {len(facebook_events)} Facebook events"
        else:
            state.message = "No Facebook events found"
        
        # Update source counts
        if "Facebook" not in state.source_counts:
            state.source_counts["Facebook"] = 0
        state.source_counts["Facebook"] += len(facebook_events) if facebook_events else 0
        
    except Exception as e:
        state.error = f"Error fetching Facebook events: {str(e)}"
        state.errors.append(f"Facebook error: {str(e)}")
    
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
    
    return patch
