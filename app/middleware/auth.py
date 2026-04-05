"""
Authentication middleware
Handles JWT token verification and user isolation
"""
from fastapi import HTTPException, Header, Depends
from typing import Optional
from supabase import Client
from app.database import get_supabase

async def verify_token(
    authorization: Optional[str] = Header(None)
) -> dict:
    """
    Verify JWT token from Authorization header
    Returns decoded token payload
    """
    if not authorization:
        raise HTTPException(
            status_code=401,
            detail="Missing authorization header"
        )
    
    try:
        # Extract token from "Bearer <token>"
        scheme, token = authorization.split()
        if scheme.lower() != "bearer":
            raise HTTPException(
                status_code=401,
                detail="Invalid authentication scheme"
            )
    except ValueError:
        raise HTTPException(
            status_code=401,
            detail="Invalid authorization header format"
        )
    
    try:
        # Verify token with Supabase
        supabase: Client = get_supabase()
        user = supabase.auth.get_user(token)
        
        if not user or not user.user:
            raise HTTPException(
                status_code=401,
                detail="Invalid token"
            )
        
        return {
            "user_id": user.user.id,
            "email": user.user.email,
            "token": token
        }
    except Exception as e:
        raise HTTPException(
            status_code=401,
            detail=f"Token verification failed: {str(e)}"
        )

async def get_current_user(
    token_data: dict = Depends(verify_token)
) -> dict:
    """Get current authenticated user"""
    return token_data
