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

    MARKET_TIMEOUT_SECONDS = 6
    FUNDAMENTAL_TIMEOUT_SECONDS = 8

    def __init__(self):
        self.last_market_debug = ""
        self.last_fundamental_debug = ""

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
            self.last_market_debug = "未识别到 6 位 A 股代码"
            print("[ChinaMarketDataService] No symbol found in user message")
            return None

        self.last_market_debug = f"开始请求 AkShare 行情: {symbol}"
        print(f"[ChinaMarketDataService] Requesting AkShare quote for {symbol}")
        try:
            quote = await asyncio.wait_for(
                asyncio.to_thread(self._fetch_akshare_quote_sync, symbol),
                timeout=self.MARKET_TIMEOUT_SECONDS,
            )
        except asyncio.TimeoutError:
            self.last_market_debug = f"AkShare 行情请求超时({self.MARKET_TIMEOUT_SECONDS}s): {symbol}"
            print(f"[ChinaMarketDataService] AkShare quote timeout for {symbol}")
            return None
        if not quote:
            if not self.last_market_debug:
                self.last_market_debug = f"AkShare 行情未返回有效数据: {symbol}"
            print(f"[ChinaMarketDataService] No quote data available for {symbol}")
            return None

        quote["symbol"] = symbol
        quote["user_intent"] = self.extract_user_intent(text)
        quote["user_change_hint"] = self.extract_change_hint(text)
        quote["source"] = "akshare"
        self.last_market_debug = f"AkShare 行情成功: {symbol}"
        print(f"[ChinaMarketDataService] AkShare quote success for {symbol}")
        return quote

    async def get_fundamental_context(self, text: str) -> Optional[dict]:
        symbol = self.extract_symbol(text)
        if not symbol:
            self.last_fundamental_debug = "未识别到 6 位 A 股代码"
            return None

        self.last_fundamental_debug = f"开始请求 AkShare 基本面: {symbol}"
        print(f"[ChinaMarketDataService] Requesting AkShare fundamentals for {symbol}")
        try:
            spot_snapshot, finance = await asyncio.wait_for(
                asyncio.gather(
                    asyncio.to_thread(self._fetch_akshare_fundamental_snapshot_sync, symbol),
                    asyncio.to_thread(self._fetch_akshare_financial_sync, symbol),
                ),
                timeout=self.FUNDAMENTAL_TIMEOUT_SECONDS,
            )
        except asyncio.TimeoutError:
            self.last_fundamental_debug = f"AkShare 基本面请求超时({self.FUNDAMENTAL_TIMEOUT_SECONDS}s): {symbol}"
            print(f"[ChinaMarketDataService] AkShare fundamentals timeout for {symbol}")
            return None

        if not spot_snapshot and not finance:
            if not self.last_fundamental_debug:
                self.last_fundamental_debug = f"AkShare 基本面未返回有效数据: {symbol}"
            print(f"[ChinaMarketDataService] No fundamental data available for {symbol}")
            return None

        merged = {"symbol": symbol, "source": "akshare"}
        if spot_snapshot:
            merged.update(spot_snapshot)
        if finance:
            merged.update(finance)
        self.last_fundamental_debug = f"AkShare 基本面成功: {symbol}"
        print(f"[ChinaMarketDataService] AkShare fundamentals success for {symbol}")
        return merged

    def _fetch_akshare_quote_sync(self, symbol: str) -> Optional[dict]:
        import akshare as ak

        snapshot = self._fetch_single_stock_snapshot_sync(symbol)
        if snapshot:
            return {
                "name": str(snapshot.get("name", "") or ""),
                "trade_date": "",
                "open": self._to_float(snapshot.get("open")),
                "close": self._to_float(snapshot.get("price")),
                "high": self._to_float(snapshot.get("high")),
                "low": self._to_float(snapshot.get("low")),
                "change": self._to_float(snapshot.get("change")),
                "pct_chg": self._to_float(snapshot.get("pct_chg")),
                "vol": self._to_float(snapshot.get("volume")),
                "amount": self._to_float(snapshot.get("amount")),
            }

        # Fallback to historical daily data if spot fails.
        try:
            hist_df = ak.stock_zh_a_hist(symbol=symbol, period="daily", adjust="")
        except Exception as exc:
            print(f"[ChinaMarketDataService] AkShare hist quote failed for {symbol}: {exc}")
            return None
        if hist_df is None or hist_df.empty:
            return None

        latest = hist_df.iloc[-1]
        return {
            "name": "",
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

    def _fetch_akshare_fundamental_snapshot_sync(self, symbol: str) -> Optional[dict]:
        snapshot = self._fetch_single_stock_snapshot_sync(symbol)
        if not snapshot:
            return None

        return {
            "name": str(snapshot.get("name", "") or ""),
            "industry": str(snapshot.get("industry", "") or ""),
            "market": self._market_label(symbol),
            "list_date": "",
            "total_mv": self._to_float(snapshot.get("market_value")),
            "circ_mv": self._to_float(snapshot.get("float_market_value")),
            "pe_ttm": self._to_float(snapshot.get("pe_ttm")),
            "pb": self._to_float(snapshot.get("pb")),
            "turnover_rate": self._to_float(snapshot.get("turnover_rate")),
        }

    def _fetch_single_stock_snapshot_sync(self, symbol: str) -> Optional[dict]:
        import akshare as ak

        try:
            quote_df = ak.stock_bid_ask_em(symbol=symbol)
        except Exception as exc:
            self.last_market_debug = f"AkShare 单股盘口请求失败: {exc}"
            print(f"[ChinaMarketDataService] AkShare bid/ask failed for {symbol}: {exc}")
            return None
        if quote_df is None or quote_df.empty:
            self.last_market_debug = f"AkShare 单股盘口为空: {symbol}"
            return None

        try:
            info_df = ak.stock_individual_info_em(symbol=symbol, timeout=15)
        except Exception as exc:
            self.last_fundamental_debug = f"AkShare 个股信息请求失败: {exc}"
            print(f"[ChinaMarketDataService] AkShare individual info failed for {symbol}: {exc}")
            info_df = None

        quote = self._frame_to_item_value_dict(quote_df)
        info = self._frame_to_item_value_dict(info_df) if info_df is not None else {}

        latest_price = (
            info.get("最新")
            or quote.get("最新")
            or quote.get("最新价")
            or quote.get("成交")
        )

        return {
            "code": symbol,
            "name": info.get("股票简称") or info.get("名称"),
            "price": latest_price,
            "industry": info.get("行业"),
            "market_value": info.get("总市值"),
            "float_market_value": info.get("流通市值"),
            "buy_1": quote.get("buy_1") or quote.get("买一"),
            "sell_1": quote.get("sell_1") or quote.get("卖一"),
            "open": quote.get("今开"),
            "high": quote.get("最高"),
            "low": quote.get("最低"),
            "change": quote.get("涨跌"),
            "pct_chg": quote.get("涨幅") or quote.get("涨跌幅"),
            "volume": quote.get("总手") or quote.get("成交量"),
            "amount": quote.get("金额") or quote.get("成交额"),
            "pe_ttm": info.get("市盈率-动态") or info.get("市盈率"),
            "pb": info.get("市净率"),
            "turnover_rate": info.get("换手率"),
        }

    def _fetch_akshare_financial_sync(self, symbol: str) -> Optional[dict]:
        import akshare as ak

        try:
            df = ak.stock_financial_analysis_indicator(symbol=symbol)
        except Exception as exc:
            self.last_fundamental_debug = f"AkShare 财务指标请求失败: {exc}"
            print(f"[ChinaMarketDataService] AkShare financial lookup failed for {symbol}: {exc}")
            return None

        if df is None or df.empty:
            self.last_fundamental_debug = f"AkShare 财务指标为空: {symbol}"
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

    def _frame_to_item_value_dict(self, df) -> dict:
        if df is None or getattr(df, "empty", True):
            return {}
        columns = {str(column) for column in df.columns}
        if {"item", "value"}.issubset(columns):
            item_key, value_key = "item", "value"
        elif {"项目", "值"}.issubset(columns):
            item_key, value_key = "项目", "值"
        elif {"item", "值"}.issubset(columns):
            item_key, value_key = "item", "值"
        else:
            return {}
        return {
            str(row[item_key]).strip(): row[value_key]
            for _, row in df.iterrows()
            if str(row[item_key]).strip()
        }

    def _market_label(self, symbol: str) -> str:
        if symbol.startswith("6"):
            return "沪A"
        if symbol.startswith(("0", "3")):
            return "深A"
        return "A股"

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
