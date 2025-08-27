from langgraph.graph import StateGraph, END
from models.workflow_state import WorkflowState
from nodes.coordination_node import coordination_node
from nodes.search_node import search_node
from nodes.scraping_node import scraping_node


def create_family_event_workflow():
    """Compile and return the LangGraph workflow for family event discovery."""

    sg = StateGraph(WorkflowState)

    # register nodes
    sg.add_node("coordinate", coordination_node)
    sg.add_node("search", search_node)
    sg.add_node("scrape", scraping_node)

    # entry point
    sg.set_entry_point("coordinate")

    # Linear flow: coordinate -> search -> scrape -> coordinate (with conditional exit)
    sg.add_edge("coordinate", "search")
    sg.add_edge("search", "scrape")
    
    # Add conditional edge from scrape back to coordinate OR to END
    sg.add_conditional_edges(
        "scrape",
        lambda state: END if state.is_complete else "coordinate",
    )

    return sg.compile()


# singleton compiled workflow
family_event_workflow = create_family_event_workflow()
