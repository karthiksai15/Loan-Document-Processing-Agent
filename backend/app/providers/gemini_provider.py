"""
Gemini LLM Provider — Phase 15 LLM Service

Uses the official google-genai SDK.
Configured via settings.GEMINI_API_KEY and settings.GEMINI_MODEL.
"""

from typing import Optional
from app.providers.base_llm_provider import (
    BaseLLMProvider,
    LLMProviderUnavailableException,
    LLMProviderQuotaExhaustedException,
)
from app.core.config import settings
from app.core.logging import logger


class GeminiProviderUnavailableException(LLMProviderUnavailableException):
    """Raised when the Gemini provider is unavailable or API key is not configured."""
    pass


class GeminiQuotaExhaustedException(GeminiProviderUnavailableException, LLMProviderQuotaExhaustedException):
    """Raised when Gemini API free-tier quota is exhausted (429 RESOURCE_EXHAUSTED)."""
    pass


class GeminiProvider(BaseLLMProvider):
    """
    LLM provider for Google Gemini using google-genai SDK.
    Configured via settings.GEMINI_API_KEY and settings.GEMINI_MODEL.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        timeout: float = 60.0,
    ):
        self.api_key = (api_key if api_key is not None else settings.GEMINI_API_KEY) or ""
        self.model = model or settings.GEMINI_MODEL or "gemini-3.5-flash-lite"
        self.timeout = timeout

    def is_available(self) -> bool:
        """Returns True if the API key is configured and non-empty."""
        return bool(self.api_key and self.api_key.strip())

    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """
        Generates text completion from Gemini via google-genai SDK.
        Returns raw JSON string.
        Fails cleanly with GeminiProviderUnavailableException if API key is missing.
        """
        if not self.is_available():
            raise GeminiProviderUnavailableException(
                "Gemini API provider is unavailable: GEMINI_API_KEY is not configured in environment or .env file."
            )

        try:
            from google import genai
            from google.genai import types
            from google.genai import errors
        except ImportError as e:
            logger.error(f"google-genai SDK is not installed: {e}")
            raise RuntimeError(f"google-genai SDK missing: {e}")

        try:
            client = genai.Client(api_key=self.api_key)
            config = types.GenerateContentConfig(
                temperature=0.1,
                response_mime_type="application/json",
                system_instruction=system_prompt if system_prompt else None,
            )

            try:
                response = client.models.generate_content(
                    model=self.model,
                    contents=prompt,
                    config=config,
                )
                return response.text or ""
            except errors.ClientError as e:
                err_str = str(e).lower()
                # 1. Detect 429 quota exhaustion (do not confuse with temporary rate limits)
                if e.code == 429 or "quota" in err_str or "resource_exhausted" in err_str or "free_tier" in err_str:
                    logger.error(f"GeminiProvider: Quota exhausted (429): {e}")
                    raise GeminiQuotaExhaustedException(f"Gemini API quota exhausted (429): {e}")

                # 2. Detect 401/403 fatal authentication errors
                if e.code in (401, 403) or "unauthorized" in err_str or "api_key" in err_str or "permission" in err_str:
                    logger.error(f"GeminiProvider: Authentication/Authorization failure: {e}")
                    raise GeminiProviderUnavailableException(f"Gemini API authentication failed ({e.code}): {e}")

                # 3. Handle model not found or unavailable (NO automatic fallback to other models)
                if e.code == 404 or "not found" in err_str or "no longer available" in err_str:
                    logger.error(f"GeminiProvider: Model '{self.model}' is unavailable or not found: {e}")
                    raise GeminiProviderUnavailableException(
                        f"Gemini model '{self.model}' is unavailable or not found ({e.code}): {e}"
                    )
                raise
            except errors.ServerError as e:
                err_str = str(e).lower()
                if e.code == 503 or "unavailable" in err_str or "high demand" in err_str:
                    logger.warning(f"GeminiProvider: Service temporarily unavailable (503): {e}")
                    raise GeminiProviderUnavailableException(f"Gemini API service temporarily unavailable (503): {e}")
                raise
        except (GeminiQuotaExhaustedException, GeminiProviderUnavailableException):
            raise
        except TimeoutError as e:
            logger.warning(f"GeminiProvider: Request timed out: {e}")
            raise GeminiProviderUnavailableException(f"Gemini API request timed out: {e}")
        except Exception as e:
            err_str = str(e).lower()
            if "quota" in err_str or "resource_exhausted" in err_str:
                raise GeminiQuotaExhaustedException(f"Gemini API quota exhausted: {e}")
            if "503" in err_str or "unavailable" in err_str:
                raise GeminiProviderUnavailableException(f"Gemini API temporarily unavailable: {e}")
            logger.error(f"GeminiProvider API call failed: {e}")
            raise RuntimeError(f"Gemini API error: {e}")

    def name(self) -> str:
        return f"GeminiProvider({self.model})"
