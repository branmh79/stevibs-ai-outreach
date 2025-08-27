from models.workflow_state import WorkflowState
from tools.google_search import GoogleSearchTool

google_tool = GoogleSearchTool()

def search_node(state: WorkflowState) -> dict:
    """LangGraph node that performs a Google search for the current category."""

    if state.current_category is None:
        # Nothing to do
        return {}

    try:
        input_payload = {
            "location": state.location,
            "event_type": state.current_category,
            "num_results": 5,
        }
        result = google_tool(input_payload)
        if result["success"]:
            state.search_results = result
        else:
            state.errors.append(
                f"Google search failed for {state.current_category}: {result.get('error')}"
            )
            state.search_results = None
    except Exception as e:
        state.errors.append(f"Google search exception: {str(e)}")
        state.search_results = None

    patch = {}
    if state.search_results is not None:
        patch["search_results"] = state.search_results
    if state.errors:
        patch["errors"] = state.errors
    return patch
