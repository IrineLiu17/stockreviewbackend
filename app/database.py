"""
Database connection and initialization
"""
from supabase import create_client, Client
from app.config import settings
import asyncpg
from typing import Optional

# Supabase client
supabase: Optional[Client] = None

def get_supabase() -> Client:
    """Get the server-side Supabase client.

    API routes authenticate the caller first and scope every query by user_id.
    The service key is needed here because an anon client without the caller's
    access token is filtered by RLS and cannot read the user's notes.
    """
    global supabase
    if supabase is None:
        supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_KEY)
    return supabase

async def get_db_pool():
    """Get async PostgreSQL connection pool"""
    return await asyncpg.create_pool(settings.DATABASE_URL)

async def init_db():
    """Initialize database tables"""
    # Tables should be created via Supabase migrations
    # This function can be used for any additional setup
    pass
