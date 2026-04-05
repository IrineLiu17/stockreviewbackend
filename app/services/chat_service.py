"""
Chat Service - Lightweight MVP coach chat built on recent reflections.
"""
from __future__ import annotations

import json
from datetime import datetime

from app.services.china_market_data_service import ChinaMarketDataService
from app.services.note_service import NoteService
from app.services.llm_service import LLMService


class ChatService:
    """Builds context from recent reflections and generates a coach reply."""

    def __init__(self):
        self.note_service = NoteService()
        self.llm_service = LLMService()
        self.market_data_service = ChinaMarketDataService()

    async def chat_with_coach(self, user_id: str, message: str) -> dict:
        notes = await self.note_service.list_notes(user_id=user_id, limit=12)
        market_context = await self.market_data_service.get_market_context(message)
        fundamental_context = await self.market_data_service.get_fundamental_context(message)
        market_chat = self._is_market_chat(message)
        analysis_mode = self._is_analysis_mode(message, market_context, fundamental_context)

        if not notes and not market_context:
            return {
                "reply": "我是小稳教练。你还没有复盘记录，先随便写一句今天的交易感受也可以；如果你想聊A股，也可以直接告诉我标的、涨跌和你现在最想做的动作。",
                "references": [],
                "used_reflection_count": 0
            }

        if self._is_recommend_request(message) and not market_context:
            return {
                "reply": "我不直接替你推荐股票，但如果你给我一只A股代码，或告诉我你更想找稳一点、成长一点还是低估值一点的票，我可以按框架陪你拆开看。",
                "references": [],
                "used_reflection_count": 0
            }

        if market_chat and not market_context:
            return {
                "reply": "如果你想聊这只A股，告诉我股票代码、今天大概涨跌多少，以及你现在更想追、抄、割还是先躺着，我再陪你把这笔动作拆开看。",
                "references": [],
                "used_reflection_count": 0
            }

        selected_notes = self._select_relevant_notes(notes, message)
        reflection_context = self._build_context(selected_notes)
        market_context_text = self._build_market_context_text(market_context)
        fundamental_context_text = self._build_fundamental_context_text(fundamental_context)
        messages = self._build_messages(
            message=message,
            reflection_context=reflection_context,
            market_context=market_context_text,
            fundamental_context=fundamental_context_text,
            analysis_mode=analysis_mode,
        )
        reply = await self.llm_service.generate_with_messages(messages)
        cleaned_reply = self._clean_reply(reply) or "今天先从一句最真实的感受开始也很好，我会继续陪你慢慢复盘。"

        return {
            "reply": cleaned_reply,
            "references": list(dict.fromkeys(self._format_reference(note.date) for note in selected_notes)),
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
        if not notes:
            return "暂无复盘记录。"
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

    def _build_market_context_text(self, market_context: dict | None) -> str:
        if not market_context:
            return "暂无A股行情数据。"

        name = market_context.get("name") or ""
        display_name = f"{name}（{market_context['symbol']}）" if name else market_context["symbol"]
        source = market_context.get("source") or "unknown"
        user_hint_parts = []
        if market_context.get("user_change_hint"):
            user_hint_parts.append(f"用户口述涨跌：{market_context['user_change_hint']}")
        if market_context.get("user_intent"):
            user_hint_parts.append(f"用户当前动作倾向：{market_context['user_intent']}")
        user_hint = "；".join(user_hint_parts) if user_hint_parts else "用户没有明确说出动作或涨跌幅。"

        return (
            f"标的：{display_name}\n"
            f"数据来源：{source}\n"
            f"最近交易日：{market_context.get('trade_date') or '未知'}\n"
            f"收盘价：{market_context.get('close')}\n"
            f"涨跌幅：{market_context.get('pct_chg')}%\n"
            f"涨跌额：{market_context.get('change')}\n"
            f"日内区间：{market_context.get('low')} - {market_context.get('high')}\n"
            f"成交量：{market_context.get('vol')}\n"
            f"成交额：{market_context.get('amount')}\n"
            f"{user_hint}"
        )

    def _build_fundamental_context_text(self, fundamental_context: dict | None) -> str:
        if not fundamental_context:
            return "暂无A股基本面数据。"

        name = fundamental_context.get("name") or ""
        display_name = f"{name}（{fundamental_context['symbol']}）" if name else fundamental_context["symbol"]
        return (
            f"标的：{display_name}\n"
            f"行业：{fundamental_context.get('industry') or '未知'}\n"
            f"市场板块：{fundamental_context.get('market') or '未知'}\n"
            f"上市日期：{fundamental_context.get('list_date') or '未知'}\n"
            f"总市值(万元)：{fundamental_context.get('total_mv')}\n"
            f"流通市值(万元)：{fundamental_context.get('circ_mv')}\n"
            f"PE(TTM)：{fundamental_context.get('pe_ttm')}\n"
            f"PB：{fundamental_context.get('pb')}\n"
            f"换手率：{fundamental_context.get('turnover_rate')}\n"
            f"ROE：{fundamental_context.get('roe')}\n"
            f"营收同比：{fundamental_context.get('or_yoy')}\n"
            f"扣非净利同比：{fundamental_context.get('netprofit_yoy')}\n"
            f"资产负债率：{fundamental_context.get('debt_to_assets')}\n"
            f"毛利率：{fundamental_context.get('grossprofit_margin')}\n"
            f"财务期末：{fundamental_context.get('end_date') or '未知'}"
        )

    def _build_messages(
        self,
        message: str,
        reflection_context: str,
        market_context: str,
        fundamental_context: str,
        analysis_mode: bool,
    ) -> list[dict]:
        system_prompt = self._build_system_prompt(analysis_mode)

        user_prompt = f"""
用户当前问题：
{message}

这是用户最近的相关复盘记录：
{reflection_context}

这是当前可用的A股事实数据：
{market_context}

这是当前可用的A股基本面数据：
{fundamental_context}

请基于这些记录，像“小稳教练”一样给出一段自然、温和、鼓励式的回复。
"""

        return [
            {"role": "system", "content": system_prompt.strip()},
            {"role": "user", "content": user_prompt.strip()},
        ]

    def _clean_reply(self, reply: str | None) -> str:
        """
        Enforce "chatty" response shape:
        - single line (no newlines)
        - <= 180 chars (approx; good enough for CN text)
        """
        text = (reply or "").strip()
        if not text:
            return ""
        # Collapse whitespace/newlines to a single space.
        text = " ".join(text.split())
        if len(text) > 180:
            text = text[:180].rstrip()
        return text

    def _build_system_prompt(self, analysis_mode: bool) -> str:
        if analysis_mode:
            return """
你叫小稳教练，现在要以“有实战感的A股交易前辈”身份回答。
你只能基于上下文里的A股事实数据、基本面数据和用户复盘记录来回答；信息不够时要直接说看不出来。

回答时必须遵守：
1 语气自然，像真人，不要每次都模板式夸奖用户
2 先说你对这只票当前状态的一个判断框架，比如偏趋势、偏震荡、偏估值、偏业绩、偏情绪
3 如果有基本面数据，就用1到2个最关键指标说人话，不要堆术语
4 不直接推荐买哪只股票，不给确定性买卖指令，不承诺收益
5 要指出一个主要风险，再给一个可执行的观察点
6 像聊天，不要 markdown，不要分标题，不要换行，控制在220字以内
"""
        return """
你叫小稳教练，是一位温和、稳定、值得信赖的交易复盘陪伴教练。
你只能基于用户提供的问题，以及上下文里的复盘记录和A股事实数据来回答；如果上下文里没有足够信息，要明确说“这一点我暂时还看不出来”。

回答时必须遵守：
1 语气自然温和，不要过度模板化
2 回答优先聚焦用户自己的交易行为、情绪模式和风险节奏
3 只有在上下文里明确给出A股事实数据时，才能引用行情；绝不能编造实时新闻、行情或财报
4 如果用户在聊A股，但缺少股票代码、涨跌幅或动作倾向，就礼貌追问这三项里缺的关键信息
5 不给确定性的买卖指令，不替用户下结论，只做条件化提醒和风控陪伴
6 尽量给一个用户明天或下一笔交易就能做到的小动作
7 如果有行情数据，先用一句人话解释当前局面，再回到用户的情绪与执行
8 控制在180字以内，像聊天，不要用 markdown，不要分标题，不要换行
"""

    def _is_market_chat(self, text: str) -> bool:
        if self.market_data_service.extract_symbol(text):
            return True
        keywords = [
            "行情", "A股", "大盘", "涨", "跌", "追", "抄", "割", "躺", "股票",
            "仓位", "止损", "买", "卖", "代码", "个股", "上证", "深证", "创业板"
        ]
        return any(keyword in text for keyword in keywords)

    def _is_analysis_mode(
        self,
        text: str,
        market_context: dict | None,
        fundamental_context: dict | None,
    ) -> bool:
        analysis_keywords = [
            "基本面", "分析", "估值", "财务", "业绩", "roe", "pe", "pb",
            "怎么看", "这票", "这只股", "还能拿吗", "能买吗", "值不值", "推荐"
        ]
        if self.market_data_service.extract_symbol(text) and ("怎么样" in text or "咋样" in text):
            return True
        return bool(market_context or fundamental_context) and any(
            keyword.lower() in text.lower() for keyword in analysis_keywords
        )

    def _is_recommend_request(self, text: str) -> bool:
        keywords = ["推荐", "荐股", "还有什么股", "买什么股", "推一个股"]
        return any(keyword in text for keyword in keywords)

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
