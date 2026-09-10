"""
Groq LLM Provider — Phase 15 LLM Service

Calls Groq API endpoint (https://api.groq.com/openai/v1/chat/completions) directly via httpx.
No OpenAI SDK dependency.
"""

from typing import Optional, List, Dict, Any
import httpx

from app.providers.base_llm_provider import BaseLLMProvider, LLMProviderUnavailableException
from app.core.config import settings
from app.core.logging import logger


class GroqProviderUnavailableException(LLMProviderUnavailableException):
    """Raised when the Groq provider is unavailable or API key is not configured."""
    pass


class GroqProvider(BaseLLMProvider):
    """
    LLM provider for Groq API using direct HTTP calls via httpx.
    Configured via settings.GROQ_API_KEY, settings.GROQ_MODEL, and settings.GROQ_BASE_URL.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: float = 60.0,
    ):
        self.api_key = (api_key if api_key is not None else settings.GROQ_API_KEY) or ""
        self.model = model or settings.GROQ_MODEL or "openai/gpt-oss-20b"
        raw_url = base_url or settings.GROQ_BASE_URL or "https://api.groq.com/openai/v1"
        self.base_url = raw_url.rstrip("/")
        self.timeout = timeout

    def is_available(self) -> bool:
        """Returns True if the API key is configured and non-empty."""
        return bool(self.api_key and self.api_key.strip())

    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """
        Generates text completion from Groq via REST API.
        Fails cleanly if API key is missing.
        """
        if not self.is_available():
            raise GroqProviderUnavailableException(
                "Groq API provider is unavailable: GROQ_API_KEY is not configured in environment or .env file."
            )

        messages: List[Dict[str, str]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.1,
            "max_tokens": 2048,
            "response_format": {"type": "json_object"},
        }

        endpoint = f"{self.base_url}/chat/completions"

        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(endpoint, headers=headers, json=payload)
                response.raise_for_status()
                data = response.json()
                choices = data.get("choices", [])
                if not choices:
                    raise RuntimeError("Groq API response contained no choices.")
                content = choices[0].get("message", {}).get("content", "")
                return content or ""
        except httpx.HTTPStatusError as e:
            logger.error(f"GroqProvider HTTP error: {e.response.status_code}")
            raise RuntimeError(f"Groq API HTTP error ({e.response.status_code}): {e.response.text}")
        except GroqProviderUnavailableException:
            raise
        except Exception as e:
            logger.error(f"GroqProvider API call failed: {e}")
            raise RuntimeError(f"Groq API error: {e}")

    def name(self) -> str:
        return f"GroqProvider({self.model})"
