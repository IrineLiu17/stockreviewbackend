"""
China Market Data Service
AkShare-only A-share quote/fundamental helper for coach chat.
"""
from __future__ import annotations

import asyncio
import re
from typing import Optional


class ChinaMarketDataService:
    """Small A-share quote helper for chat enrichment."""

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

    async def get_market_context(self, text: str) -> Optional[dict]:
        symbol = self.extract_symbol(text)
        if not symbol:
            print("[ChinaMarketDataService] No symbol found in user message")
            return None

        print(f"[ChinaMarketDataService] Requesting AkShare quote for {symbol}")
        quote = await asyncio.to_thread(self._fetch_akshare_quote_sync, symbol)
        if not quote:
            print(f"[ChinaMarketDataService] No quote data available for {symbol}")
            return None

        quote["symbol"] = symbol
        quote["user_intent"] = self.extract_user_intent(text)
        quote["user_change_hint"] = self.extract_change_hint(text)
        quote["source"] = "akshare"
        print(f"[ChinaMarketDataService] AkShare quote success for {symbol}")
        return quote

    async def get_fundamental_context(self, text: str) -> Optional[dict]:
        symbol = self.extract_symbol(text)
        if not symbol:
            return None

        print(f"[ChinaMarketDataService] Requesting AkShare fundamentals for {symbol}")
        profile, finance = await asyncio.gather(
            asyncio.to_thread(self._fetch_akshare_profile_sync, symbol),
            asyncio.to_thread(self._fetch_akshare_financial_sync, symbol),
        )

        if not profile and not finance:
            print(f"[ChinaMarketDataService] No fundamental data available for {symbol}")
            return None

        merged = {"symbol": symbol, "source": "akshare"}
        if profile:
            merged.update(profile)
        if finance:
            merged.update(finance)
        print(f"[ChinaMarketDataService] AkShare fundamentals success for {symbol}")
        return merged

    def _fetch_akshare_quote_sync(self, symbol: str) -> Optional[dict]:
        import akshare as ak

        hist_df = ak.stock_zh_a_hist(symbol=symbol, period="daily", adjust="")
        if hist_df is None or hist_df.empty:
            return None

        latest = hist_df.iloc[-1]
        spot_name = ""
        try:
            spot_df = ak.stock_zh_a_spot_em()
            matched = spot_df[spot_df["代码"].astype(str) == symbol]
            if not matched.empty:
                spot_name = str(matched.iloc[0].get("名称", ""))
        except Exception as exc:
            print(f"[ChinaMarketDataService] AkShare spot lookup failed for {symbol}: {exc}")

        return {
            "name": spot_name,
            "trade_date": str(latest.get("日期", "")).replace("-", ""),
            "open": self._to_float(latest.get("开盘")),
            "close": self._to_float(latest.get("收盘")),
            "high": self._to_float(latest.get("最高")),
            "low": self._to_float(latest.get("最低")),
            "change": self._to_float(latest.get("涨跌额")),
            "pct_chg": self._to_float(latest.get("涨跌幅")),
            "vol": self._to_float(latest.get("成交量")),
            "amount": self._to_float(latest.get("成交额")),
        }

    def _fetch_akshare_profile_sync(self, symbol: str) -> Optional[dict]:
        import akshare as ak

        try:
            info_df = ak.stock_individual_info_em(symbol=symbol)
        except Exception as exc:
            print(f"[ChinaMarketDataService] AkShare profile lookup failed for {symbol}: {exc}")
            return None

        if info_df is None or info_df.empty:
            return None

        mapping = {
            str(row["item"]).strip(): row["value"]
            for _, row in info_df.iterrows()
            if "item" in info_df.columns and "value" in info_df.columns
        }

        return {
            "name": str(mapping.get("股票简称", "") or ""),
            "industry": str(mapping.get("行业", "") or ""),
            "market": str(mapping.get("上市时间", "") or ""),
            "list_date": str(mapping.get("上市时间", "") or ""),
            "total_mv": self._to_float(mapping.get("总市值")),
            "circ_mv": self._to_float(mapping.get("流通市值")),
        }

    def _fetch_akshare_financial_sync(self, symbol: str) -> Optional[dict]:
        import akshare as ak

        try:
            df = ak.stock_financial_analysis_indicator(symbol=symbol)
        except Exception as exc:
            print(f"[ChinaMarketDataService] AkShare financial lookup failed for {symbol}: {exc}")
            return None

        if df is None or df.empty:
            return None

        latest = df.iloc[0]
        return {
            "end_date": str(latest.get("日期", "") or ""),
            "roe": self._pick_float(latest, ["净资产收益率(%)", "净资产收益率", "ROE"]),
            "or_yoy": self._pick_float(latest, ["主营业务收入增长率(%)", "主营业务收入增长率"]),
            "netprofit_yoy": self._pick_float(latest, ["净利润增长率(%)", "净利润增长率"]),
            "debt_to_assets": self._pick_float(latest, ["资产负债率(%)", "资产负债率"]),
            "grossprofit_margin": self._pick_float(latest, ["毛利率(%)", "毛利率"]),
            "pe_ttm": self._pick_float(latest, ["市盈率TTM", "市盈率"]),
            "pb": self._pick_float(latest, ["市净率", "PB"]),
        }

    def _pick_float(self, row, keys: list[str]) -> Optional[float]:
        for key in keys:
            if key in row:
                value = self._to_float(row.get(key))
                if value is not None:
                    return value
        return None

    def _to_float(self, value) -> Optional[float]:
        try:
            if value is None or value == "":
                return None
            text = str(value).replace(",", "").replace("%", "").strip()
            if not text or text == "--":
                return None
            return float(text)
        except Exception:
            return None
