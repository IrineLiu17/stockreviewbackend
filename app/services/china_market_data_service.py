"""
China Market Data Service
Fetches lightweight A-share quote context from Tushare for coach chat.
"""
from __future__ import annotations

import re
from typing import Optional

import httpx

from app.config import settings


class ChinaMarketDataService:
    """Small A-share quote helper for chat enrichment."""

    TUSHARE_URL = "http://api.tushare.pro"

    async def get_market_context(self, text: str) -> Optional[dict]:
        symbol = self.extract_symbol(text)
        if not symbol or not settings.TUSHARE_TOKEN:
            return None

        ts_code = self._to_ts_code(symbol)
        quote = await self._fetch_latest_daily_quote(ts_code)
        if not quote:
            return None

        return {
            "symbol": symbol,
            "ts_code": ts_code,
            "name": await self._fetch_stock_name(ts_code),
            "trade_date": quote.get("trade_date", ""),
            "close": quote.get("close"),
            "pct_chg": quote.get("pct_chg"),
            "change": quote.get("change"),
            "open": quote.get("open"),
            "high": quote.get("high"),
            "low": quote.get("low"),
            "vol": quote.get("vol"),
            "amount": quote.get("amount"),
            "user_intent": self.extract_user_intent(text),
            "user_change_hint": self.extract_change_hint(text),
        }

    def extract_symbol(self, text: str) -> Optional[str]:
        patterns = [
            r"\b(6\d{5}|0\d{5}|3\d{5})\b",
            r"\b(?:sh|sz|SH|SZ)[ .-]?(\d{6})\b",
        ]
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1)
        return None

    def extract_user_intent(self, text: str) -> str:
        lowered = text.lower()
        intent_keywords = [
            ("追", ["追", "追高", "追涨"]),
            ("抄", ["抄", "抄底"]),
            ("割", ["割", "止损", "割肉"]),
            ("躺", ["躺", "拿着", "不动", "继续持有"]),
            ("加仓", ["加仓"]),
            ("减仓", ["减仓"]),
            ("卖出", ["卖", "卖出"]),
            ("买入", ["买", "买入"]),
        ]
        for label, keywords in intent_keywords:
            if any(keyword in lowered for keyword in keywords):
                return label
        return ""

    def extract_change_hint(self, text: str) -> str:
        match = re.search(r"([+-]?\d+(?:\.\d+)?)\s*%", text)
        if match:
            return f"{match.group(1)}%"
        match = re.search(r"(涨|跌)\s*(\d+(?:\.\d+)?)\s*%", text)
        if match:
            prefix = "+" if match.group(1) == "涨" else "-"
            return f"{prefix}{match.group(2)}%"
        return ""

    def _to_ts_code(self, symbol: str) -> str:
        if symbol.startswith(("6", "9")):
            return f"{symbol}.SH"
        return f"{symbol}.SZ"

    async def _fetch_latest_daily_quote(self, ts_code: str) -> Optional[dict]:
        payload = {
            "api_name": "daily",
            "token": settings.TUSHARE_TOKEN,
            "params": {"ts_code": ts_code, "limit": 1},
            "fields": "ts_code,trade_date,open,high,low,close,pre_close,change,pct_chg,vol,amount",
        }
        data = await self._post_tushare(payload)
        if not data:
            return None
        items = self._records_to_dicts(data)
        return items[0] if items else None

    async def _fetch_stock_name(self, ts_code: str) -> str:
        payload = {
            "api_name": "stock_basic",
            "token": settings.TUSHARE_TOKEN,
            "params": {"ts_code": ts_code},
            "fields": "ts_code,symbol,name",
        }
        data = await self._post_tushare(payload)
        if not data:
            return ""
        items = self._records_to_dicts(data)
        return str(items[0].get("name", "")) if items else ""

    async def _post_tushare(self, payload: dict) -> Optional[dict]:
        try:
            async with httpx.AsyncClient(timeout=12.0) as client:
                response = await client.post(self.TUSHARE_URL, json=payload)
                response.raise_for_status()
                body = response.json()
                if body.get("code") != 0:
                    return None
                return body.get("data")
        except Exception:
            return None

    def _records_to_dicts(self, data: dict) -> list[dict]:
        fields = data.get("fields") or []
        items = data.get("items") or []
        return [dict(zip(fields, row)) for row in items]
