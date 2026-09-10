from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
import httpx
from app.core.config import settings
from app.core.logging import logger

class BaseLLMProvider(ABC):
    """
    Abstract Base Class for LLM Providers.
    Supports free/local providers: Gemini API (free tier) & Ollama (local).
    """
    
    @abstractmethod
    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """Generate text completion from prompt."""
        pass
        
    @abstractmethod
    def name(self) -> str:
        """Return provider implementation name."""
        pass


class GeminiProvider(BaseLLMProvider):
    """
    Gemini API Provider implementation using google-genai SDK.
    Primary LLM provider.
    """
    
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or settings.GEMINI_API_KEY
        self.model = model or settings.GEMINI_MODEL
        self._client = None
        
        if self.api_key:
            try:
                from google import genai
                self._client = genai.Client(api_key=self.api_key)
            except Exception as e:
                logger.warning(f"Failed to initialize Gemini client: {e}")

    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        if not self._client:
            raise ValueError("Gemini API key is not configured or client failed to initialize.")
        
        try:
            full_prompt = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt
            response = self._client.models.generate_content(
                model=self.model,
                contents=full_prompt,
            )
            return response.text or ""
        except Exception as e:
            logger.error(f"Gemini API generation error: {e}")
            raise RuntimeError(f"Gemini API error: {e}")

    def name(self) -> str:
        return f"GeminiProvider({self.model})"


class OllamaProvider(BaseLLMProvider):
    """
    Ollama Provider implementation for local zero-cost LLM inference.
    Fallback provider.
    """
    
    def __init__(self, base_url: Optional[str] = None, model: Optional[str] = None):
        self.base_url = base_url or settings.OLLAMA_BASE_URL
        self.model = model or settings.OLLAMA_MODEL

    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        url = f"{self.base_url.rstrip('/')}/api/generate"
        payload: Dict[str, Any] = {
            "model": self.model,
            "prompt": prompt,
            "stream": False
        }
        if system_prompt:
            payload["system"] = system_prompt
            
        try:
            with httpx.Client(timeout=60.0) as client:
                response = client.post(url, json=payload)
                response.raise_for_status()
                data = response.json()
                return data.get("response", "")
        except Exception as e:
            logger.error(f"Ollama local LLM error: {e}")
            raise RuntimeError(f"Ollama provider error: {e}")

    def name(self) -> str:
        return f"OllamaProvider({self.model})"


def get_llm_provider(provider_type: Optional[str] = None) -> BaseLLMProvider:
    """
    Factory function to instantiate the active LLM Provider based on configuration.
    Defaults to settings.LLM_PROVIDER ('gemini' or 'ollama').
    """
    selected = provider_type or settings.LLM_PROVIDER
    
    if selected.lower() == "gemini":
        return GeminiProvider()
    elif selected.lower() == "ollama":
        return OllamaProvider()
    else:
        raise ValueError(f"Unsupported LLM provider type: {selected}")
