"""
Agent Service - Agno: AI-powered analysis agent
Handles AI analysis with tools (YFinance, Note Manager, Long-term Memory)
"""
import asyncio
from typing import AsyncIterator, Optional
from datetime import datetime, timedelta
from uuid import UUID
import json

from app.config import settings
from app.services.note_service import NoteService
from app.services.tools.yfinance_tool import YFinanceTool
from app.services.tools.memory_tool import MemoryTool
from app.services.llm_service import LLMService

class AgentService:
    """Agent service for AI-powered analysis"""
    
    def __init__(self):
        self.note_service = NoteService()
        self.llm_service = LLMService()
        self.yfinance_tool = YFinanceTool()
        self.memory_tool = MemoryTool()
    
    async def analyze_note_async(
        self,
        note_id: UUID,
        user_id: str
    ):
        """Analyze note asynchronously and update database"""
        # Get note
        note = await self.note_service.get_note(note_id, user_id)
        if not note:
            return
        
        # Run analysis in background
        asyncio.create_task(self._analyze_and_update(note_id, user_id, note))
    
    async def _analyze_and_update(
        self,
        note_id: UUID,
        user_id: str,
        note
    ):
        """Internal method to analyze and update note"""
        try:
            # Get analysis
            analysis, sentiment = await self._generate_analysis(note, user_id)
            
            # Update note
            await self.note_service.update_note(
                note_id=note_id,
                user_id=user_id,
                ai_feedback=analysis,
                sentiment_score=sentiment
            )
        except Exception as e:
            print(f"Error analyzing note {note_id}: {e}")
    
    async def analyze_note_stream(
        self,
        note_id: UUID,
        user_id: str
    ) -> AsyncIterator[str]:
        """Stream AI analysis for real-time display"""
        # Get note
        note = await self.note_service.get_note(note_id, user_id)
        if not note:
            return
        
        # Get context from tools
        context = await self._build_context(note, user_id)
        
        # Stream analysis
        async for chunk in self.llm_service.stream_analysis(
            note=note,
            context=context
        ):
            yield chunk
        
        # Calculate sentiment and update
        full_analysis = await self._get_full_analysis(note, context)
        sentiment = self._calculate_sentiment(full_analysis)
        
        await self.note_service.update_note(
            note_id=note_id,
            user_id=user_id,
            ai_feedback=full_analysis,
            sentiment_score=sentiment
        )
    
    async def _build_context(
        self,
        note,
        user_id: str
    ) -> dict:
        """Build context for AI analysis using tools"""
        context = {
            "note": {
                "date": note.date.isoformat() if isinstance(note.date, datetime) else note.date,
                "question1": note.question1,
                "question2": note.question2,
                "question3": note.question3,
            },
            "market_data": {},
            "historical_patterns": []
        }
        
        # Get market data (if stock symbols mentioned)
        try:
            market_data = await self.yfinance_tool.get_market_context(note)
            context["market_data"] = market_data
        except Exception as e:
            print(f"Error fetching market data: {e}")
        
        # Get historical patterns (past week)
        try:
            patterns = await self.memory_tool.get_weekly_patterns(user_id)
            context["historical_patterns"] = patterns
        except Exception as e:
            print(f"Error fetching historical patterns: {e}")
        
        return context
    
    async def _generate_analysis(
        self,
        note,
        user_id: str
    ) -> tuple[str, float]:
        """Generate AI analysis"""
        context = await self._build_context(note, user_id)
        analysis = await self._get_full_analysis(note, context)
        sentiment = self._calculate_sentiment(analysis)
        return analysis, sentiment
    
    async def _get_full_analysis(
        self,
        note,
        context: dict
    ) -> str:
        """Get full AI analysis"""
        prompt = self._build_prompt(note, context)
        return await self.llm_service.generate_analysis(prompt)
    
    def _build_prompt(
        self,
        note,
        context: dict
    ) -> str:
        """Build prompt for AI analysis"""
        date_str = note.date.strftime("%Y年%m月%d日") if isinstance(note.date, datetime) else str(note.date)
        
        prompt = f"""你是一位专业的交易心理分析师和交易教练，你擅长帮助交易者分析他们的交易反思并提供具有建设性的建议。

今天日期: {date_str}

交易者的反思:

1. 问题: 今天的交易行为是否遵循原始交易策略？
交易者回答: {note.question1}

2. 问题: 是否有任何决策是基于情绪而做出的？
交易者回答: {note.question2}

3. 问题: 明天计划调整仓位或策略吗？
交易者回答: {note.question3}
"""
        
        # Add market context if available
        if context.get("market_data"):
            prompt += f"\n市场数据:\n{json.dumps(context['market_data'], ensure_ascii=False, indent=2)}\n"
        
        # Add historical patterns if available
        if context.get("historical_patterns"):
            prompt += f"\n过去一周的情绪模式:\n{json.dumps(context['historical_patterns'], ensure_ascii=False, indent=2)}\n"
        
        prompt += """
请根据以上信息提供简洁明了的分析和建议，包括:
1. 对交易者心态的分析
2. 对交易纪律的评估
3. 针对性的改进建议
4. 一句鼓励的话

请确保回答专业、简洁且具有针对性。不要使用markdown格式，不要添加标题，不要包含字数统计，直接以正常段落文字回复即可。总字数控制在300字以内。
"""
        
        return prompt
    
    def _calculate_sentiment(self, analysis: str) -> float:
        """Calculate sentiment score from analysis (-1 to 1)"""
        # Simple sentiment analysis based on keywords
        positive_keywords = ["好", "优秀", "进步", "改善", "成功", "正确", "良好", "积极"]
        negative_keywords = ["问题", "错误", "风险", "注意", "避免", "危险", "消极", "担忧"]
        
        analysis_lower = analysis.lower()
        positive_count = sum(1 for word in positive_keywords if word in analysis_lower)
        negative_count = sum(1 for word in negative_keywords if word in analysis_lower)
        
        if positive_count + negative_count == 0:
            return 0.0
        
        # Normalize to -1 to 1
        sentiment = (positive_count - negative_count) / max(positive_count + negative_count, 1)
        return max(-1.0, min(1.0, sentiment))
