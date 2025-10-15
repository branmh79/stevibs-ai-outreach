# backend/routes/auth.py
from fastapi import APIRouter, HTTPException, status, Depends
from datetime import timedelta
from auth.models import LoginRequest, LoginResponse, UserInfo
from auth.utils import authenticate_user, create_access_token, ACCESS_TOKEN_EXPIRE_MINUTES
from auth.dependencies import get_current_user

router = APIRouter()

@router.post("/login", response_model=LoginResponse)
async def login(credentials: LoginRequest):
    """
    Authenticate a user and return a JWT token.
    """
    user = authenticate_user(credentials.username, credentials.password)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Create access token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={
            "sub": user["username"],
            "location": user["location"],
            "full_name": user["full_name"]
        },
        expires_delta=access_token_expires
    )
    
    return LoginResponse(
        access_token=access_token,
        token_type="bearer",
        username=user["username"],
        location=user["location"],
        full_name=user["full_name"]
    )

@router.get("/me", response_model=UserInfo)
async def get_current_user_info(current_user: dict = Depends(get_current_user)):
    """
    Get information about the currently authenticated user.
    """
    return UserInfo(
        username=current_user["username"],
        location=current_user["location"],
        full_name=current_user["full_name"]
    )

