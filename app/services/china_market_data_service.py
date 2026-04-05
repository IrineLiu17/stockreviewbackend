"""
China Market Data Service
Fetches lightweight A-share quote context from Tushare for coach chat.
"""
from __future__ import annotations

import asyncio
import re
from typing import Optional

import httpx

from app.config import settings


class ChinaMarketDataService:
    """Small A-share quote helper for chat enrichment."""

    TUSHARE_URL = "http://api.tushare.pro"

    async def get_market_context(self, text: str) -> Optional[dict]:
        symbol = self.extract_symbol(text)
        if not symbol:
            print("[ChinaMarketDataService] No symbol found in user message")
            return None

        ts_code = self._to_ts_code(symbol)
        print(f"[ChinaMarketDataService] symbol={symbol} ts_code={ts_code}")

        quote: Optional[dict] = None
        source = ""

        if settings.TUSHARE_TOKEN:
            print(f"[ChinaMarketDataService] Requesting Tushare for {ts_code}")
            quote = await self._fetch_latest_daily_quote(ts_code)
            if quote:
                source = "tushare"
                print(f"[ChinaMarketDataService] Tushare success for {ts_code}")
            else:
                print(f"[ChinaMarketDataService] Tushare returned no data for {ts_code}")
        else:
            print("[ChinaMarketDataService] TUSHARE_TOKEN missing, skip Tushare")

        if not quote:
            print(f"[ChinaMarketDataService] Requesting AkShare for {symbol}")
            quote = await self._fetch_akshare_quote(symbol)
            if quote:
                source = "akshare"
                print(f"[ChinaMarketDataService] AkShare success for {symbol}")
            else:
                print(f"[ChinaMarketDataService] AkShare returned no data for {symbol}")

        if not quote:
            print(f"[ChinaMarketDataService] No market context available for {symbol}")
            return None

        return {
            "symbol": symbol,
            "ts_code": ts_code,
            "name": await self._fetch_stock_name(ts_code) or quote.get("name", ""),
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
            "source": source,
        }

    async def get_fundamental_context(self, text: str) -> Optional[dict]:
        symbol = self.extract_symbol(text)
        if not symbol or not settings.TUSHARE_TOKEN:
            return None

        ts_code = self._to_ts_code(symbol)
        print(f"[ChinaMarketDataService] Requesting fundamentals for {ts_code}")

        profile_task = self._fetch_stock_profile(ts_code)
        valuation_task = self._fetch_daily_basic(ts_code)
        finance_task = self._fetch_fina_indicator(ts_code)
        profile, valuation, finance = await asyncio.gather(
            profile_task, valuation_task, finance_task
        )

        if not profile and not valuation and not finance:
            print(f"[ChinaMarketDataService] No fundamental data available for {ts_code}")
            return None

        return {
            "symbol": symbol,
            "ts_code": ts_code,
            "name": (profile or {}).get("name", ""),
            "industry": (profile or {}).get("industry", ""),
            "market": (profile or {}).get("market", ""),
            "list_date": (profile or {}).get("list_date", ""),
            "trade_date": (valuation or {}).get("trade_date", ""),
            "total_mv": self._to_float((valuation or {}).get("total_mv")),
            "circ_mv": self._to_float((valuation or {}).get("circ_mv")),
            "pe_ttm": self._to_float((valuation or {}).get("pe_ttm")),
            "pb": self._to_float((valuation or {}).get("pb")),
            "turnover_rate": self._to_float((valuation or {}).get("turnover_rate_f")),
            "end_date": (finance or {}).get("end_date", ""),
            "roe": self._to_float((finance or {}).get("roe")),
            "or_yoy": self._to_float((finance or {}).get("or_yoy")),
            "netprofit_yoy": self._to_float((finance or {}).get("q_dtprofit_yoy")),
            "debt_to_assets": self._to_float((finance or {}).get("debt_to_assets")),
            "grossprofit_margin": self._to_float((finance or {}).get("grossprofit_margin")),
            "source": "tushare",
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
        if not settings.TUSHARE_TOKEN:
            return ""
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

    async def _fetch_stock_profile(self, ts_code: str) -> Optional[dict]:
        payload = {
            "api_name": "stock_basic",
            "token": settings.TUSHARE_TOKEN,
            "params": {"ts_code": ts_code},
            "fields": "ts_code,symbol,name,industry,market,list_date",
        }
        data = await self._post_tushare(payload)
        if not data:
            return None
        items = self._records_to_dicts(data)
        return items[0] if items else None

    async def _fetch_daily_basic(self, ts_code: str) -> Optional[dict]:
        payload = {
            "api_name": "daily_basic",
            "token": settings.TUSHARE_TOKEN,
            "params": {"ts_code": ts_code, "limit": 1},
            "fields": "ts_code,trade_date,total_mv,circ_mv,pe_ttm,pb,turnover_rate_f",
        }
        data = await self._post_tushare(payload)
        if not data:
            return None
        items = self._records_to_dicts(data)
        return items[0] if items else None

    async def _fetch_fina_indicator(self, ts_code: str) -> Optional[dict]:
        payload = {
            "api_name": "fina_indicator",
            "token": settings.TUSHARE_TOKEN,
            "params": {"ts_code": ts_code, "limit": 1},
            "fields": "ts_code,end_date,roe,or_yoy,q_dtprofit_yoy,debt_to_assets,grossprofit_margin",
        }
        data = await self._post_tushare(payload)
        if not data:
            return None
        items = self._records_to_dicts(data)
        return items[0] if items else None

    async def _post_tushare(self, payload: dict) -> Optional[dict]:
        try:
            async with httpx.AsyncClient(timeout=12.0) as client:
                response = await client.post(self.TUSHARE_URL, json=payload)
                response.raise_for_status()
                body = response.json()
                if body.get("code") != 0:
                    print(f"[ChinaMarketDataService] Tushare error body={body}")
                    return None
                return body.get("data")
        except Exception as exc:
            print(f"[ChinaMarketDataService] Tushare request failed: {exc}")
            return None

    def _records_to_dicts(self, data: dict) -> list[dict]:
        fields = data.get("fields") or []
        items = data.get("items") or []
        return [dict(zip(fields, row)) for row in items]

    async def _fetch_akshare_quote(self, symbol: str) -> Optional[dict]:
        try:
            return await asyncio.to_thread(self._fetch_akshare_quote_sync, symbol)
        except Exception as exc:
            print(f"[ChinaMarketDataService] AkShare request failed: {exc}")
            return None

    def _fetch_akshare_quote_sync(self, symbol: str) -> Optional[dict]:
        import akshare as ak

        df = ak.stock_zh_a_hist(
            symbol=symbol,
            period="daily",
            adjust="",
        )
        if df is None or df.empty:
            return None

        latest = df.iloc[-1]
        trade_date = str(latest.get("日期", ""))
        open_price = self._to_float(latest.get("开盘"))
        close_price = self._to_float(latest.get("收盘"))
        high_price = self._to_float(latest.get("最高"))
        low_price = self._to_float(latest.get("最低"))
        change = self._to_float(latest.get("涨跌额"))
        pct_chg = self._to_float(latest.get("涨跌幅"))
        volume = self._to_float(latest.get("成交量"))
        amount = self._to_float(latest.get("成交额"))

        name = ""
        try:
            spot_df = ak.stock_zh_a_spot_em()
            matched = spot_df[spot_df["代码"].astype(str) == symbol]
            if not matched.empty:
                name = str(matched.iloc[0].get("名称", ""))
        except Exception as exc:
            print(f"[ChinaMarketDataService] AkShare spot lookup failed for {symbol}: {exc}")

        return {
            "trade_date": trade_date.replace("-", ""),
            "open": open_price,
            "close": close_price,
            "high": high_price,
            "low": low_price,
            "change": change,
            "pct_chg": pct_chg,
            "vol": volume,
            "amount": amount,
            "name": name,
        }

    def _to_float(self, value) -> Optional[float]:
        try:
            if value is None or value == "":
                return None
            return float(value)
        except Exception:
            return None
