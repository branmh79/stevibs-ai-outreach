from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

class EventData(BaseModel):
    """Represents a single event scraped from the web."""

    title: Optional[str] = None
    description: Optional[str] = None
    website: Optional[str] = None
    when: Optional[str] = None  # e.g., day_time_sentence
    address: Optional[str] = None  # Location/venue information
    interested_count: Optional[int] = None
    attending_count: Optional[int] = None
    contact_email: Optional[str] = None  # retained for other tools
    phone_number: Optional[str] = None
    source: str = "family_scraper"
    category: Optional[str] = None

class WorkflowState(BaseModel):
    """Centralised LangGraph state that is passed between nodes."""

    # --- immutable user-provided params ---
    location: str
    use_mock: bool = False
    search_radius: int = 5000

    # --- coordination ---
    current_category: Optional[str] = None
    is_complete: bool = False

    # --- data collected along the way ---
    events: List[EventData] = Field(default_factory=list)
    source_counts: Dict[str, int] = Field(default_factory=dict)
    errors: List[str] = Field(default_factory=list)
    error: Optional[str] = None
    message: Optional[str] = None

    # intermediate scratch pads
    search_results: Optional[Dict[str, Any]] = None
    scraped_data: Optional[List[Dict[str, Any]]] = None
