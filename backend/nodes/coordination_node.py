from typing import List
from models.workflow_state import WorkflowState

FAMILY_CATEGORIES: List[str] = [
    "indoor events",
    "after school programs",
    "family recreation center",
    "community center",
    "youth activities",
    "teen programs",
    "family events",
    "school events",
    "community events",
    "youth sports clubs",
]

async def coordination_node(state: WorkflowState) -> dict:
    """Control node that iterates over family categories until complete."""

    # If we've already processed everything, just return
    if state.is_complete:
        return {}

    # If no current category, start with the first one
    if state.current_category is None:
        state.current_category = FAMILY_CATEGORIES[0]
        return {"current_category": state.current_category}

    # Move to the next category if possible
    try:
        idx = FAMILY_CATEGORIES.index(state.current_category)
        if idx + 1 < len(FAMILY_CATEGORIES):
            state.current_category = FAMILY_CATEGORIES[idx + 1]
        else:
            # No more categories – mark complete
            state.current_category = None
            state.is_complete = True
    except ValueError:
        # In case current_category got out of sync
        state.current_category = None
        state.is_complete = True

    # Return only fields that changed and are not None to satisfy diff-based updates
    patch = {}
    if state.current_category is not None:
        patch["current_category"] = state.current_category
    if state.is_complete:
        patch["is_complete"] = True
    return patch
