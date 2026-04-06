"""
Data models for the application
"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from uuid import UUID

class ReflectionNote(BaseModel):
    """Reflection note model"""
    id: Optional[UUID] = None
    user_id: str
    date: datetime
    question1: str = Field(..., description="是否遵循原始交易策略")
    question2: str = Field(..., description="是否有情绪决策")
    question3: str = Field(..., description="明天计划调整")
    ai_feedback: Optional[str] = None
    sentiment_score: Optional[float] = Field(None, ge=-1.0, le=1.0)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

class ReflectionNoteCreate(BaseModel):
    """Create reflection note request"""
    date: datetime
    question1: str
    question2: str
    question3: str

class ReflectionNoteUpdate(BaseModel):
    """Update reflection note request"""
    question1: Optional[str] = None
    question2: Optional[str] = None
    question3: Optional[str] = None

class ReflectionNoteResponse(BaseModel):
    """Reflection note response"""
    id: UUID
    user_id: str
    date: datetime
    question1: str
    question2: str
    question3: str
    ai_feedback: Optional[str] = None
    sentiment_score: Optional[float] = None
    created_at: datetime
    updated_at: datetime

class NoteListResponse(BaseModel):
    """List of notes response"""
    notes: list[ReflectionNoteResponse]
    total: int

class AnalysisRequest(BaseModel):
    """Request for AI analysis"""
    question1: str
    question2: str
    question3: str
    date: datetime
    user_id: str

class UserProfile(BaseModel):
    """User profile model"""
    id: str
    email: Optional[str] = None
    subscription_tier: str = "free"
    created_at: datetime

class CoachChatRequest(BaseModel):
    """Chat request for XiaoWen coach."""
    message: str = Field(..., min_length=1, max_length=1000)

class CoachChatResponse(BaseModel):
    """Chat response for XiaoWen coach."""
    reply: str
    references: list[str] = []
    used_reflection_count: int = 0
    debug: Optional[str] = None
