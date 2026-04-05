"""
Database connection and initialization
"""
from supabase import create_client, Client
from app.config import settings
import asyncpg
from typing import Optional

# Supabase client
supabase: Optional[Client] = None
supabase_admin: Optional[Client] = None

def get_supabase() -> Client:
    """Get Supabase client"""
    global supabase
    if supabase is None:
        supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
    return supabase

def get_supabase_admin() -> Client:
    """
    Get Supabase admin client (service role).
    Use this for server-side DB reads/writes to avoid RLS blocking.
    """
    global supabase_admin
    if supabase_admin is None:
        supabase_admin = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_KEY)
    return supabase_admin

async def get_db_pool():
    """Get async PostgreSQL connection pool"""
    if not settings.DATABASE_URL:
        raise ValueError("DATABASE_URL not set")
    return await asyncpg.create_pool(settings.DATABASE_URL)

async def init_db():
    """Initialize database tables"""
    # Tables should be created via Supabase migrations
    # This function can be used for any additional setup
    pass
