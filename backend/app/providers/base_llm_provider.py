"""
Base LLM Provider — Phase 15 GenAI Foundation

Defines the contract for all Phase 15 LLM providers (Groq, Fake).
Kept separate from app/core/llm.py (Gemini/Ollama, Phase 3) to avoid coupling.
"""

from abc import ABC, abstractmethod
from typing import Optional


class LLMProviderUnavailableException(Exception):
    """Raised when an LLM provider is unavailable or API key is not configured."""
    pass


class LLMProviderQuotaExhaustedException(LLMProviderUnavailableException):
    """Raised when an LLM provider request quota is exhausted (429 RESOURCE_EXHAUSTED)."""
    pass


class BaseLLMProvider(ABC):
    """
    Abstract base for Phase 15 LLM providers.

    Providers must implement:
      - generate(prompt, system_prompt) -> str   (raw text generation)
      - name() -> str                            (human-readable identifier)
    """

    @abstractmethod
    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """
        Generate a text completion.

        Args:
            prompt:        The user-facing instruction (may reference structured context).
            system_prompt: Optional system-level instruction (trusted; injected at top).

        Returns:
            Raw string output from the LLM.
        """
        ...

    @abstractmethod
    def name(self) -> str:
        """Human-readable provider/model identifier, e.g. 'GroqProvider(openai/gpt-oss-20b)'."""
        ...
