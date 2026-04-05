"""
Application configuration
"""
from pydantic_settings import BaseSettings
from typing import List

class Settings(BaseSettings):
    # Supabase
    SUPABASE_URL: str
    SUPABASE_KEY: str
    SUPABASE_SERVICE_KEY: str
    
    # Database
    # Optional for MVP: most operations use Supabase HTTP APIs.
    # Only required if you use asyncpg features / direct Postgres access.
    DATABASE_URL: str = ""
    
    # OpenAI/DeepSeek
    OPENAI_API_KEY: str = ""
    DEEPSEEK_API_KEY: str = ""
    LLM_PROVIDER: str = "deepseek"  # "openai" or "deepseek"
    
    # China market data
    TUSHARE_TOKEN: str = ""
    
    # JWT
    JWT_SECRET: str
    JWT_ALGORITHM: str = "HS256"
    
    # CORS
    CORS_ORIGINS: List[str] = ["*"]
    
    # Agent
    AGENT_MODEL: str = "deepseek-chat"  # or "gpt-4o"
    AGENT_TEMPERATURE: float = 0.7
    
    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()
