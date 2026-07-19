"""
FastAPI Backend for Stock Review App
Main entry point for the API gateway
"""
from fastapi import FastAPI, Depends, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from contextlib import asynccontextmanager
import os
from typing import Optional

from app.database import init_db
from app.routers import notes, auth, health, verification, chat
from app.middleware.auth import verify_token, get_current_user
from app.config import settings

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize database on startup"""
    await init_db()
    yield
    # Cleanup if needed

app = FastAPI(
    title="Stock Review API",
    description="Backend API for Stock Review App with Agent-powered analysis",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router, prefix="/api", tags=["health"])
app.include_router(auth.router, prefix="/api/auth", tags=["authentication"])
app.include_router(notes.router, prefix="/api/notes", tags=["notes"])
app.include_router(verification.router, prefix="/api/verification", tags=["verification"])
app.include_router(chat.router, prefix="/api/chat", tags=["chat"])

@app.get("/")
async def root():
    return {"message": "Stock Review API", "version": "1.0.0"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8000)),
        reload=True
    )
