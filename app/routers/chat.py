"""
Chat routes - MVP coach chat based on recent reflection history.
"""
from fastapi import APIRouter, Depends, HTTPException

from app.middleware.auth import get_current_user
from app.models import CoachChatRequest, CoachChatResponse
from app.services.chat_service import ChatService

router = APIRouter()


@router.post("/coach", response_model=CoachChatResponse)
async def chat_with_coach(
    body: CoachChatRequest,
    current_user: dict = Depends(get_current_user)
):
    """Chat with XiaoWen coach using recent reflections as lightweight context."""
    try:
        service = ChatService()
        result = await service.chat_with_coach(
            user_id=current_user["user_id"],
            message=body.message.strip()
        )
        return CoachChatResponse(**result)
    except Exception as exc:
        raise HTTPException(status_code=503, detail="小稳教练暂时无法回复，请稍后再试") from exc
