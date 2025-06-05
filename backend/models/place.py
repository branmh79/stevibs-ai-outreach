from pydantic import BaseModel, HttpUrl, EmailStr
from typing import Optional

class Place(BaseModel):
    name: str
    description: Optional[str]
    address: str
    website: Optional[HttpUrl]
    contact_email: Optional[EmailStr]
    phone_number: Optional[str]
