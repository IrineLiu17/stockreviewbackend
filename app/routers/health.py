"""
Health check endpoint
"""
from fastapi import APIRouter
from datetime import datetime, timezone

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
