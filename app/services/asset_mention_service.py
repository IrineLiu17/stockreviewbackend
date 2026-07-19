"""Extract and persist normalized assets mentioned in reflection text."""

import asyncio
import re
from functools import lru_cache
from typing import Any

import akshare as ak
from supabase import create_client

from app.config import settings


class AssetMentionService:
    CODE_PATTERN = re.compile(r"(?<!\d)(\d{6})(?!\d)")
    TICKER_PATTERN = re.compile(r"(?<![A-Za-z])\$?([A-Z]{2,5})(?![A-Za-z])")
    TICKER_STOP_WORDS = {
        "ETF", "USD", "THE", "AND", "FOR", "WITH", "THIS", "THAT",
        "BUY", "SELL", "HOLD", "LONG", "SHORT", "FOMO", "AI", "K", "OK"
    }

    def __init__(self):
        # The API has already authenticated the caller; use the server client
        # for database access and keep every query scoped by user_id.
        self.supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_KEY)

    @staticmethod
    def _normalize_text(value: str) -> str:
        return re.sub(r"\s+", "", value).upper()

    @staticmethod
    @lru_cache(maxsize=1)
    def _a_share_name_map() -> dict[str, str]:
        """Cache the exchange name list; it is refreshed with a new process."""
        try:
            frame = ak.stock_info_a_code_name()
            return {
                str(row["名称"]).strip(): str(row["代码"]).zfill(6)
                for _, row in frame.iterrows()
                if row.get("名称") and row.get("代码")
            }
        except Exception as exc:
            print(f"[AssetMentionService] failed to load A-share names: {exc}")
            return {}

    @classmethod
    def _extract_mentions(cls, fields: dict[str, str]) -> list[dict[str, Any]]:
        name_map = cls._a_share_name_map()
        normalized_full_text = "\n".join(fields.values())
        results: dict[tuple[str, str], dict[str, Any]] = {}

        # Names are the primary path. Longest names first avoids partial matches.
        for name in sorted(name_map, key=len, reverse=True):
            if name not in normalized_full_text:
                continue
            code = name_map[name]
            field = next((key for key, value in fields.items() if name in value), "question1")
            results[("cn", code)] = {
                "market": "cn",
                "symbol": code,
                "asset_name": name,
                "asset_type": "stock",
                "source_field": field,
                "matched_text": name,
                "confidence": 1.0,
            }

        # Six-digit codes supplement name matching.
        for field, text in fields.items():
            for code in cls.CODE_PATTERN.findall(text):
                results.setdefault(("cn", code), {
                    "market": "cn",
                    "symbol": code,
                    "asset_name": next((name for name, mapped in name_map.items() if mapped == code), None),
                    "asset_type": "stock",
                    "source_field": field,
                    "matched_text": code,
                    "confidence": 1.0,
                })

            # Preserve obvious Latin tickers such as QQQ and KLAC from the user's notes.
            for ticker in cls.TICKER_PATTERN.findall(text.upper()):
                if ticker in cls.TICKER_STOP_WORDS:
                    continue
                results.setdefault(("ticker", ticker), {
                    "market": "unknown",
                    "symbol": ticker,
                    "asset_name": None,
                    "asset_type": "ticker",
                    "source_field": field,
                    "matched_text": ticker,
                    "confidence": 0.85,
                })

        return list(results.values())

    async def sync_note(self, note_id: str, user_id: str) -> list[dict[str, Any]]:
        note_result = await asyncio.to_thread(
            lambda: self.supabase.table("reflection_notes")
            .select("question1,question2,question3")
            .eq("id", note_id)
            .eq("user_id", user_id)
            .single()
            .execute()
        )
        if not note_result.data:
            return []

        fields = {
            "question1": note_result.data.get("question1") or "",
            "question2": note_result.data.get("question2") or "",
            "question3": note_result.data.get("question3") or "",
        }
        mentions = await asyncio.to_thread(self._extract_mentions, fields)

        await asyncio.to_thread(
            lambda: self.supabase.table("reflection_asset_mentions")
            .delete()
            .eq("reflection_id", note_id)
            .eq("user_id", user_id)
            .execute()
        )
        if mentions:
            rows = [{"reflection_id": note_id, "user_id": user_id, **mention} for mention in mentions]
            await asyncio.to_thread(
                lambda: self.supabase.table("reflection_asset_mentions")
                .insert(rows)
                .execute()
            )
        return mentions
