from models.workflow_state import WorkflowState
from tools.churches import ChurchesTool

def churches_node(state: WorkflowState) -> WorkflowState:
    """
    Node that fetches church events from configured church websites.
    Uses custom selectors for each church to scrape event data.
    """
    print(f"[NODE] Churches node called for location: {state.location}")
    
    try:
        # Initialize the churches tool
        churches_tool = ChurchesTool()
        
        # Execute the tool
        result = churches_tool.execute(
            location=state.location,
            start_date=None,  # TODO: Add date range support to WorkflowState if needed
            end_date=None
        )
        
        if result.get("success", False):
            church_events_raw = result.get("events", [])
            print(f"[NODE] Churches tool found {len(church_events_raw)} events")
            
            # Convert raw events to EventData objects
            from models.workflow_state import EventData
            church_events = []
            for event_data in church_events_raw:
                try:
                    event = EventData(
                        title=event_data.get("title"),
                        description=event_data.get("description"),
                        website=event_data.get("url"),
                        when=event_data.get("when"),  # Use the formatted date
                        address=event_data.get("location"),
                        source=event_data.get("source", "church"),
                        category="church"
                    )
                    church_events.append(event)
                except Exception as e:
                    print(f"[WARNING] Failed to convert event to EventData: {str(e)}")
                    continue
            
            # Add church events to the state
            existing_events = list(state.events)
            all_events = existing_events + church_events
            
            # Create updated state as dictionary for LangGraph
            return {
                "events": all_events,
                "message": f"Churches: {len(church_events)} events found"
            }
        else:
            error_msg = result.get("error", "Unknown error")
            print(f"[NODE] Churches tool failed: {error_msg}")
            
            # Update state with error info as dictionary for LangGraph
            return {
                "errors": state.errors + [f"Churches: {error_msg}"],
                "message": f"Churches: failed - {error_msg}"
            }
            
    except Exception as e:
        print(f"[NODE] Churches node error: {str(e)}")
        
        # Update state with error info as dictionary for LangGraph
        return {
            "errors": state.errors + [f"Churches node: {str(e)}"],
            "message": f"Churches: error - {str(e)}"
        }
