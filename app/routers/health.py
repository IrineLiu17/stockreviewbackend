"""
Health check endpoint
"""
from fastapi import APIRouter, Query
from datetime import datetime, timezone
from app.services.china_market_data_service import ChinaMarketDataService

router = APIRouter()

APP_VERSION = "1.0.0"
DEPLOY_TRACK = "single-stock-akshare-snapshot"
DEPLOY_COMMIT = "989e430"

@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "stock-review-api",
        "version": APP_VERSION,
        "track": DEPLOY_TRACK,
        "commit": DEPLOY_COMMIT,
    }


@router.get("/debug/version")
async def debug_version():
    """Public version/debug endpoint for deployment verification."""
    return {
        "service": "stock-review-api",
        "version": APP_VERSION,
        "track": DEPLOY_TRACK,
        "commit": DEPLOY_COMMIT,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/debug/chat-probe")
async def debug_chat_probe(
    message: str = Query(..., min_length=1, description="Probe message such as 000001怎么样")
):
    """Public market-data probe endpoint for debugging live A-share lookups."""
    service = ChinaMarketDataService()
    market_context = await service.get_market_context(message)
    fundamental_context = await service.get_fundamental_context(message)
    return {
        "message": message,
        "symbol": service.extract_symbol(message),
        "market_debug": service.last_market_debug,
        "fundamental_debug": service.last_fundamental_debug,
        "market_context": market_context,
        "fundamental_context": fundamental_context,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
