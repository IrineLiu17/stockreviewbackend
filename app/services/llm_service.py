"""
LLM Service - Handles communication with OpenAI/DeepSeek
"""
import httpx
import json
from typing import AsyncIterator
from app.config import settings

class LLMService:
    """Service for LLM API calls"""
    
    def __init__(self):
        self.api_key = settings.DEEPSEEK_API_KEY if settings.LLM_PROVIDER == "deepseek" else settings.OPENAI_API_KEY
        self.model = settings.AGENT_MODEL
        self.base_url = "https://api.deepseek.com" if settings.LLM_PROVIDER == "deepseek" else "https://api.openai.com/v1"
    
    async def generate_analysis(self, prompt: str) -> str:
        """Generate analysis (non-streaming)"""
        async with httpx.AsyncClient(timeout=60.0) as client:
            url = f"{self.base_url}/chat/completions"
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": self.model,
                "messages": [
                    {"role": "user", "content": prompt}
                ],
                "temperature": settings.AGENT_TEMPERATURE,
                "stream": False
            }
            
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            
            data = response.json()
            return data["choices"][0]["message"]["content"]
    
    async def generate_with_messages(self, messages: list[dict]) -> str:
        """Generate completion with system + user messages (e.g. for coach feedback)."""
        if not self.api_key:
            raise ValueError("DEEPSEEK_API_KEY or OPENAI_API_KEY not set")
        async with httpx.AsyncClient(timeout=60.0) as client:
            url = f"{self.base_url}/chat/completions"
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            payload = {
                "model": self.model,
                "messages": messages,
                "temperature": 0.5,
                "stream": False
            }
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
            return (data.get("choices") or [{}])[0].get("message", {}).get("content", "")
        self,
        note,
        context: dict
    ) -> AsyncIterator[str]:
        """Stream analysis (typing effect)"""
        from app.services.agent_service import AgentService
        agent = AgentService()
        prompt = agent._build_prompt(note, context)
        
        async with httpx.AsyncClient(timeout=120.0) as client:
            url = f"{self.base_url}/chat/completions"
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": self.model,
                "messages": [
                    {"role": "user", "content": prompt}
                ],
                "temperature": settings.AGENT_TEMPERATURE,
                "stream": True
            }
            
            async with client.stream("POST", url, headers=headers, json=payload) as response:
                response.raise_for_status()
                
                async for line in response.aiter_lines():
                    if not line.strip():
                        continue
                    
                    if line.startswith("data: "):
                        data_str = line[6:]
                        if data_str == "[DONE]":
                            break
                        
                        try:
                            data = json.loads(data_str)
                            if "choices" in data and len(data["choices"]) > 0:
                                delta = data["choices"][0].get("delta", {})
                                content = delta.get("content", "")
                                if content:
                                    yield content
                        except json.JSONDecodeError:
                            continue
