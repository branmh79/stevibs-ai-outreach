from langgraph.graph import StateGraph, END
from models.workflow_state import WorkflowState
from nodes.coordination_node import coordination_node
from nodes.search_node import search_node
from nodes.facebook_events_node import facebook_events_node
from nodes.macaronikid_events_node import macaronikid_events_node


def create_family_event_workflow():
    """Compile and return the LangGraph workflow for family event discovery."""

    sg = StateGraph(WorkflowState)

    # register nodes
    sg.add_node("facebook_events", facebook_events_node)
    sg.add_node("macaronikid_events", macaronikid_events_node)

    # entry point - go to Facebook events first
    sg.set_entry_point("facebook_events")

    # Flow: facebook_events -> macaronikid_events -> END
    sg.add_edge("facebook_events", "macaronikid_events")
    sg.add_edge("macaronikid_events", END)

    return sg.compile()


# singleton compiled workflow
family_event_workflow = create_family_event_workflow()
