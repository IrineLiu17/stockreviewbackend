"""
Note Manager Tool - Custom tool for formatting and saving analysis results
This is integrated into the AgentService but can be used as a standalone tool
"""
from typing import Dict, Any
from app.services.note_service import NoteService

class NoteManagerTool:
    """Tool for managing note formatting and database operations"""
    
    def __init__(self):
        self.note_service = NoteService()
    
    async def format_analysis_result(
        self,
        analysis: str,
        sentiment_score: float
    ) -> Dict[str, Any]:
        """Format analysis result for database storage"""
        return {
            "ai_feedback": analysis,
            "sentiment_score": sentiment_score,
            "formatted": True
        }
    
    async def save_analysis(
        self,
        note_id: str,
        user_id: str,
        analysis: str,
        sentiment_score: float
    ) -> bool:
        """Save formatted analysis to database"""
        try:
            from uuid import UUID
            await self.note_service.update_note(
                note_id=UUID(note_id),
                user_id=user_id,
                ai_feedback=analysis,
                sentiment_score=sentiment_score
            )
            return True
        except Exception as e:
            print(f"Error saving analysis: {e}")
            return False
