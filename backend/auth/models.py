# backend/auth/models.py
from pydantic import BaseModel

class LoginRequest(BaseModel):
    username: str
    password: str

class LoginResponse(BaseModel):
    access_token: str
    token_type: str
    username: str
    location: str
    full_name: str

class UserInfo(BaseModel):
    username: str
    location: str
    full_name: str

