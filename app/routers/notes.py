"""
Notes routes - Handle reflection notes CRUD operations
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from typing import Optional, List
from datetime import datetime, timedelta
from uuid import UUID
import json

from app.models import (
    ReflectionNoteCreate,
    ReflectionNoteResponse,
    NoteListResponse,
    AnalysisRequest
)
from app.middleware.auth import get_current_user
from app.services.note_service import NoteService
from app.services.agent_service import AgentService
from app.services.llm_service import LLMService

router = APIRouter()

@router.post("", response_model=ReflectionNoteResponse, status_code=201)
async def create_note(
    note_data: ReflectionNoteCreate,
    current_user: dict = Depends(get_current_user)
):
    """Create a new reflection note"""
    note_service = NoteService()
    
    # Create note
    note = await note_service.create_note(
        user_id=current_user["user_id"],
        date=note_data.date,
        question1=note_data.question1,
        question2=note_data.question2,
        question3=note_data.question3
    )
    
    # Trigger AI analysis asynchronously
    # The analysis will be updated in the background
    agent_service = AgentService()
    await agent_service.analyze_note_async(note.id, current_user["user_id"])
    
    return note

@router.get("/stream/{note_id}")
async def stream_analysis(
    note_id: UUID,
    current_user: dict = Depends(get_current_user)
):
    """Stream AI analysis for a note (typing effect)"""
    note_service = NoteService()
    
    # Verify note belongs to user
    note = await note_service.get_note(note_id, current_user["user_id"])
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    
    agent_service = AgentService()
    
    async def generate_stream():
        """Generate streaming response"""
        async for chunk in agent_service.analyze_note_stream(
            note_id, 
            current_user["user_id"]
        ):
            yield f"data: {json.dumps({'chunk': chunk, 'done': False})}\n\n"
        
        # Final update
        updated_note = await note_service.get_note(note_id, current_user["user_id"])
        yield f"data: {json.dumps({'chunk': '', 'done': True, 'note': updated_note.dict()})}\n\n"
    
    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )

COACH_SYSTEM_PROMPT = """你叫小稳教练，是一位温和、稳定、值得信赖的交易复盘陪伴教练。
你的任务是根据用户的交易复盘，给出简洁、友好、鼓励式的反馈，帮助用户更愿意持续记录。
重点关注：
1 用户今天有没有做到一点点纪律
2 是否出现情绪波动、冲动交易、FOMO、犹豫或风险管理不到位
3 明天最适合做的一个小调整
输出时必须遵守：
1 语气温和，像陪伴型教练，不要居高临下，不要指责
2 先肯定用户愿意复盘这件事，再给提醒
3 优先提供能马上做到的小建议，避免空泛说教
4 不要提供具体股票买卖建议，不要制造焦虑
5 如果用户内容很少，也要先鼓励，再给简短提醒
6 issues 字段请写成“今天可以留意的地方”，表达柔和，不要写得像批评
7 summary 请像一句贴心总结，不超过50字
请严格按照以下JSON格式回复，不要其他内容：
{"summary":"总体评价内容","issues":["留意点1","留意点2"],"suggestions":["建议1","建议2"],"discipline_score":82}"""

@router.post("/ai-feedback")
async def create_ai_coach_feedback(
    body: dict,
    current_user: dict = Depends(get_current_user)
):
    """Generate AI trading coach feedback (summary, issues, suggestions, discipline_score)."""
    question1 = body.get("question1") or ""
    question2 = body.get("question2") or ""
    question3 = body.get("question3") or ""
    user_prompt = f"""用户今日复盘：
问题1：{question1}
问题2：{question2}
问题3：{question3}
请根据以上复盘进行分析。"""
    try:
        llm = LLMService()
        raw = await llm.generate_with_messages([
            {"role": "system", "content": COACH_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt}
        ])
    except Exception as e:
        raise HTTPException(status_code=503, detail="AI分析暂时不可用，请稍后再试")
    raw = raw.strip().replace("```json", "").replace("```", "").strip()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        raise HTTPException(status_code=503, detail="AI分析暂时不可用，请稍后再试")
    summary = data.get("summary") or ""
    issues = data.get("issues") or []
    suggestions = data.get("suggestions") or []
    discipline_score = data.get("discipline_score")
    if not isinstance(issues, list):
        issues = [issues] if issues else []
    if not isinstance(suggestions, list):
        suggestions = [suggestions] if suggestions else []
    return {
        "summary": summary,
        "issues": issues[:3],
        "suggestions": suggestions[:3],
        "discipline_score": discipline_score
    }

@router.get("", response_model=NoteListResponse)
async def list_notes(
    current_user: dict = Depends(get_current_user),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    search: Optional[str] = None
):
    """List user's reflection notes with filtering and search"""
    note_service = NoteService()
    
    notes = await note_service.list_notes(
        user_id=current_user["user_id"],
        skip=skip,
        limit=limit,
        start_date=start_date,
        end_date=end_date,
        search=search
    )
    
    total = await note_service.count_notes(
        user_id=current_user["user_id"],
        start_date=start_date,
        end_date=end_date,
        search=search
    )
    
    return NoteListResponse(notes=notes, total=total)

@router.get("/{note_id}", response_model=ReflectionNoteResponse)
async def get_note(
    note_id: UUID,
    current_user: dict = Depends(get_current_user)
):
    """Get a specific note"""
    note_service = NoteService()
    note = await note_service.get_note(note_id, current_user["user_id"])
    
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    
    return note

@router.delete("/{note_id}", status_code=204)
async def delete_note(
    note_id: UUID,
    current_user: dict = Depends(get_current_user)
):
    """Delete a note"""
    note_service = NoteService()
    success = await note_service.delete_note(note_id, current_user["user_id"])
    
    if not success:
        raise HTTPException(status_code=404, detail="Note not found")
    
    return None

@router.get("/history/weekly")
async def get_weekly_history(
    current_user: dict = Depends(get_current_user)
):
    """Get user's notes from the past week for agent context"""
    note_service = NoteService()
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=7)
    
    notes = await note_service.list_notes(
        user_id=current_user["user_id"],
        start_date=start_date,
        end_date=end_date,
        limit=100
    )
    
    return {
        "notes": notes,
        "period": {
            "start": start_date.isoformat(),
            "end": end_date.isoformat()
        }
    }
