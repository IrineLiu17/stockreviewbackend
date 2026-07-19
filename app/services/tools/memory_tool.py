"""
Memory Tool - Retrieves historical patterns for long-term memory
"""
from typing import List, Dict, Any
from datetime import datetime, timedelta
from app.services.note_service import NoteService

class MemoryTool:
    """Tool for retrieving historical patterns"""
    
    def __init__(self):
        self.note_service = NoteService()
    
    async def get_weekly_patterns(
        self,
        user_id: str
    ) -> List[Dict[str, Any]]:
        """Get user's patterns from the past week"""
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=7)
        
        notes = await self.note_service.list_notes(
            user_id=user_id,
            start_date=start_date,
            end_date=end_date,
            limit=100
        )
        
        patterns = []
        for note in notes:
            patterns.append({
                "date": note.date.isoformat() if isinstance(note.date, datetime) else note.date,
                "sentiment_score": note.sentiment_score,
                "has_emotional_decision": "情绪" in note.question2.lower() or "emotion" in note.question2.lower(),
                "has_strategy_deviation": "策略" in note.question1.lower() or "strategy" in note.question1.lower(),
            })
        
        return patterns
