from langgraph.graph import StateGraph, END
from models.workflow_state import WorkflowState
from nodes.coordination_node import coordination_node
from nodes.search_node import search_node
from nodes.facebook_events_node import facebook_events_node
from nodes.macaronikid_events_node import macaronikid_events_node
from nodes.schools_node import schools_node


def create_family_event_workflow():
    """Compile and return the LangGraph workflow for family event discovery."""

    sg = StateGraph(WorkflowState)

    # register nodes - TEMPORARILY USING ONLY SCHOOLS TOOL TO AVOID RATE LIMITING
    # TODO: Re-enable other tools later
    # sg.add_node("facebook_events", facebook_events_node)
    # sg.add_node("macaronikid_events", macaronikid_events_node)
    sg.add_node("schools", schools_node)

    # entry point - go to Schools events only (temporarily)
    sg.set_entry_point("schools")

    # Flow: schools -> END (simple flow while testing)
    sg.add_edge("schools", END)

    return sg.compile()


# singleton compiled workflow
family_event_workflow = create_family_event_workflow()
