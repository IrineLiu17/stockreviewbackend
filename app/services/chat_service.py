"""
Chat Service - Lightweight MVP coach chat built on recent reflections.
"""
from __future__ import annotations

import json
from datetime import datetime

from app.services.note_service import NoteService
from app.services.llm_service import LLMService


class ChatService:
    """Builds context from recent reflections and generates a coach reply."""

    def __init__(self):
        self.note_service = NoteService()
        self.llm_service = LLMService()

    async def chat_with_coach(self, user_id: str, message: str) -> dict:
        notes = await self.note_service.list_notes(user_id=user_id, limit=12)
        if not notes:
            return {
                "reply": "我是小稳教练。你还没有复盘记录，先随便写一句今天的交易感受也可以，我会再陪你一起慢慢看。",
                "references": [],
                "used_reflection_count": 0
            }

        selected_notes = self._select_relevant_notes(notes, message)
        context = self._build_context(selected_notes)
        messages = self._build_messages(message, context)
        reply = await self.llm_service.generate_with_messages(messages)
        cleaned_reply = reply.strip() or "今天先从一句最真实的感受开始也很好，我会继续陪你慢慢复盘。"

        return {
            "reply": cleaned_reply,
            "references": [self._format_reference(note.date) for note in selected_notes],
            "used_reflection_count": len(selected_notes)
        }

    def _select_relevant_notes(self, notes: list, message: str) -> list:
        scored_notes = [(self._score_note(note, message), note) for note in notes]
        scored_notes.sort(key=lambda item: (item[0], item[1].date), reverse=True)
        selected = [note for score, note in scored_notes[:4] if score > 0]
        return selected or notes[:3]

    def _score_note(self, note, message: str) -> int:
        lowered = message.lower()
        score = 0
        note_text = " ".join(
            [
                note.question1 or "",
                note.question2 or "",
                note.question3 or "",
                self._extract_feedback_summary(note.ai_feedback)
            ]
        ).lower()

        keyword_groups = {
            "emotion": ["情绪", "冲动", "慌", "害怕", "fomo", "冷静", "上头", "追高", "恐惧"],
            "plan": ["计划", "明天", "执行", "纪律", "遵守", "按计划", "操作"],
            "trade": ["交易", "买入", "卖出", "加仓", "减仓", "仓位", "止损"],
            "progress": ["最近", "这周", "进步", "改善", "变化", "问题", "复盘"]
        }

        for keywords in keyword_groups.values():
            if any(keyword in lowered for keyword in keywords):
                score += sum(2 for keyword in keywords if keyword in note_text and keyword in lowered)

        if self._contains_any(lowered, ["最近", "这周", "这几天", "一直"]):
            score += 2
        if note.ai_feedback:
            score += 1
        return score

    def _build_context(self, notes: list) -> str:
        chunks = []
        for note in notes:
            chunks.append(
                "\n".join(
                    [
                        f"[{self._format_reference(note.date)}]",
                        f"今天做了什么：{self._safe_text(note.question1)}",
                        f"不太冷静的时刻：{self._safe_text(note.question2)}",
                        f"明天计划：{self._safe_text(note.question3)}",
                        f"小稳上次总结：{self._safe_text(self._extract_feedback_summary(note.ai_feedback))}",
                    ]
                )
            )
        return "\n\n".join(chunks)

    def _build_messages(self, message: str, context: str) -> list[dict]:
        system_prompt = """
你叫小稳教练，是一位温和、稳定、值得信赖的交易复盘陪伴教练。
你只能基于用户提供的问题，以及上下文里的复盘记录来回答；如果上下文里没有足够信息，要明确说“这一点我暂时还看不出来”。

回答时必须遵守：
1 语气温和，先肯定用户愿意复盘或提问这件事
2 回答聚焦用户自己的交易行为和情绪模式，不发散
3 不编造外部市场事实，不假装知道实时新闻、行情或财报
4 不给具体股票买卖建议，不做确定性判断
5 尽量给一个用户明天就能做到的小动作
6 控制在180字以内，像聊天，不要用 markdown，不要分标题
"""

        user_prompt = f"""
用户当前问题：
{message}

这是用户最近的相关复盘记录：
{context}

请基于这些记录，像“小稳教练”一样给出一段自然、温和、鼓励式的回复。
"""

        return [
            {"role": "system", "content": system_prompt.strip()},
            {"role": "user", "content": user_prompt.strip()},
        ]

    def _extract_feedback_summary(self, ai_feedback: str | None) -> str:
        if not ai_feedback:
            return ""
        try:
            parsed = json.loads(ai_feedback)
            if isinstance(parsed, dict):
                return str(parsed.get("summary") or "")
        except json.JSONDecodeError:
            pass
        return ai_feedback

    def _safe_text(self, value: str | None) -> str:
        text = (value or "").strip()
        return text if text else "未填写"

    def _format_reference(self, date_value) -> str:
        if isinstance(date_value, datetime):
            return date_value.strftime("%Y-%m-%d")
        try:
            parsed = datetime.fromisoformat(str(date_value).replace("Z", "+00:00"))
            return parsed.strftime("%Y-%m-%d")
        except ValueError:
            return str(date_value)

    def _contains_any(self, text: str, keywords: list[str]) -> bool:
        return any(keyword in text for keyword in keywords)
