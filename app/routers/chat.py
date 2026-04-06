"""
Chat routes - MVP coach chat based on recent reflection history.
"""
import json

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

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


@router.post("/coach/stream")
async def stream_chat_with_coach(
    body: CoachChatRequest,
    current_user: dict = Depends(get_current_user)
):
    """Stream chat with XiaoWen coach for better perceived latency."""
    service = ChatService()

    async def event_generator():
        try:
            status_event = {
                "type": "status",
                "message": "服务器已收到请求，正在准备上下文",
            }
            yield f"data: {json.dumps(status_event, ensure_ascii=False)}\n\n"
            async for event in service.stream_chat_with_coach(
                user_id=current_user["user_id"],
                message=body.message.strip()
            ):
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
        except Exception:
            error_event = {
                "type": "error",
                "message": "小稳教练暂时无法回复，请稍后再试",
            }
            yield f"data: {json.dumps(error_event, ensure_ascii=False)}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
