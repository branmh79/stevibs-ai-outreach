from pydantic import BaseModel, HttpUrl, EmailStr
from typing import Optional, List

class EnrichedEvent(BaseModel):
    title: str
    date: Optional[str] = None  # Date the event occurs
    description: Optional[str] = None
    contact_email: Optional[EmailStr] = None
    phone: Optional[str] = None
    website: Optional[HttpUrl] = None

class EnrichedEventList(BaseModel):
    events: List[EnrichedEvent]

class EventSearchParams(BaseModel):
    location: str
    event_type: Optional[str] = "Summer Camp"
    start_date: Optional[str] = None  # Format: YYYY-MM-DD
    end_date: Optional[str] = None
