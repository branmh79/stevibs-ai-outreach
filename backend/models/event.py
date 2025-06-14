from pydantic import BaseModel, HttpUrl, EmailStr
from typing import Optional, List

class EnrichedEvent(BaseModel):
    title: str
    date: Optional[str] = None  # Now explicitly optional with a default
    description: Optional[str] = None
    contact_email: Optional[EmailStr] = None
    phone: Optional[str] = None
    website: Optional[HttpUrl] = None

class EnrichedEventList(BaseModel):
    events: List[EnrichedEvent]
