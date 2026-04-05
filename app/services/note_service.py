"""
Note Service - Handles database operations for reflection notes
"""
from typing import Optional, List
from datetime import datetime
from uuid import UUID
from app.database import get_supabase
from app.models import ReflectionNoteResponse
from supabase import Client

class NoteService:
    """Service for managing reflection notes"""
    
    def __init__(self):
        self.supabase: Client = get_supabase()
        self.table_name = "reflection_notes"
    
    async def create_note(
        self,
        user_id: str,
        date: datetime,
        question1: str,
        question2: str,
        question3: str
    ) -> ReflectionNoteResponse:
        """Create a new reflection note"""
        data = {
            "user_id": user_id,
            "date": date.isoformat(),
            "question1": question1,
            "question2": question2,
            "question3": question3,
        }
        
        result = self.supabase.table(self.table_name).insert(data).execute()
        
        if not result.data:
            raise Exception("Failed to create note")
        
        return ReflectionNoteResponse(**result.data[0])
    
    async def get_note(
        self,
        note_id: UUID,
        user_id: str
    ) -> Optional[ReflectionNoteResponse]:
        """Get a note by ID (with user isolation)"""
        result = self.supabase.table(self.table_name)\
            .select("*")\
            .eq("id", str(note_id))\
            .eq("user_id", user_id)\
            .execute()
        
        if not result.data:
            return None
        
        return ReflectionNoteResponse(**result.data[0])
    
    async def list_notes(
        self,
        user_id: str,
        skip: int = 0,
        limit: int = 20,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        search: Optional[str] = None
    ) -> List[ReflectionNoteResponse]:
        """List notes with filtering"""
        query = self.supabase.table(self.table_name)\
            .select("*")\
            .eq("user_id", user_id)\
            .order("date", desc=True)\
            .range(skip, skip + limit - 1)
        
        if start_date:
            query = query.gte("date", start_date.isoformat())
        
        if end_date:
            query = query.lte("date", end_date.isoformat())
        
        if search:
            # Search in all text fields
            query = query.or_(
                f"question1.ilike.%{search}%,question2.ilike.%{search}%,question3.ilike.%{search}%"
            )
        
        result = query.execute()
        
        return [ReflectionNoteResponse(**item) for item in result.data]
    
    async def count_notes(
        self,
        user_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        search: Optional[str] = None
    ) -> int:
        """Count notes matching criteria"""
        query = self.supabase.table(self.table_name)\
            .select("id", count="exact")\
            .eq("user_id", user_id)
        
        if start_date:
            query = query.gte("date", start_date.isoformat())
        
        if end_date:
            query = query.lte("date", end_date.isoformat())
        
        if search:
            query = query.or_(
                f"question1.ilike.%{search}%,question2.ilike.%{search}%,question3.ilike.%{search}%"
            )
        
        result = query.execute()
        return result.count if hasattr(result, 'count') else len(result.data)
    
    async def update_note(
        self,
        note_id: UUID,
        user_id: str,
        ai_feedback: Optional[str] = None,
        sentiment_score: Optional[float] = None
    ) -> Optional[ReflectionNoteResponse]:
        """Update note with AI analysis"""
        update_data = {
            "updated_at": datetime.utcnow().isoformat()
        }
        
        if ai_feedback is not None:
            update_data["ai_feedback"] = ai_feedback
        
        if sentiment_score is not None:
            update_data["sentiment_score"] = sentiment_score
        
        result = self.supabase.table(self.table_name)\
            .update(update_data)\
            .eq("id", str(note_id))\
            .eq("user_id", user_id)\
            .execute()
        
        if not result.data:
            return None
        
        return ReflectionNoteResponse(**result.data[0])
    
    async def delete_note(
        self,
        note_id: UUID,
        user_id: str
    ) -> bool:
        """Delete a note"""
        result = self.supabase.table(self.table_name)\
            .delete()\
            .eq("id", str(note_id))\
            .eq("user_id", user_id)\
            .execute()
        
        return len(result.data) > 0
