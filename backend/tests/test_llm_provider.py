import pytest
from app.core.llm import get_llm_provider, GeminiProvider, OllamaProvider

def test_get_gemini_provider():
    provider = get_llm_provider("gemini")
    assert isinstance(provider, GeminiProvider)
    assert "GeminiProvider" in provider.name()

def test_get_ollama_provider():
    provider = get_llm_provider("ollama")
    assert isinstance(provider, OllamaProvider)
    assert "OllamaProvider" in provider.name()

def test_unsupported_provider():
    with pytest.raises(ValueError):
        get_llm_provider("unsupported_llm_type")


def test_gemini_provider_uses_configured_model():
    """Verify GeminiProvider defaults to settings.GEMINI_MODEL without hardcoded values."""
    from app.core.config import settings
    from app.providers.gemini_provider import GeminiProvider

    assert settings.GEMINI_MODEL == "gemini-3.5-flash-lite"
    p = GeminiProvider()
    assert p.model == "gemini-3.5-flash-lite"
    assert "gemini-3.5-flash-lite" in p.name()


def test_gemini_provider_no_automatic_model_fallback_on_unavailable():
    """
    Prove that GeminiProvider does NOT automatically fall back to gemini-3.6-flash
    or any other model when the configured model is unavailable.
    """
    from unittest.mock import patch, MagicMock
    from app.providers.gemini_provider import GeminiProvider, GeminiProviderUnavailableException
    from google.genai import errors

    provider = GeminiProvider(api_key="fake-test-key-000", model="gemini-3.5-flash-lite")

    with patch("google.genai.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client.models.generate_content.side_effect = errors.ClientError(
            code=404,
            response_json={"error": {"message": "models/gemini-3.5-flash-lite is not found"}}
        )

        with pytest.raises(GeminiProviderUnavailableException) as exc_info:
            provider.generate("Test prompt for model fallback verification")

        assert "gemini-3.5-flash-lite" in str(exc_info.value)
        # Verify generate_content was called EXACTLY once — no second call to gemini-3.6-flash
        assert mock_client.models.generate_content.call_count == 1
        called_model = mock_client.models.generate_content.call_args.kwargs.get("model")
        assert called_model == "gemini-3.5-flash-lite"
        assert called_model != "gemini-3.6-flash"


def test_gemini_provider_quota_exhaustion_no_model_fallback():
    """Verify 429 quota exhaustion raises GeminiQuotaExhaustedException with zero model switching."""
    from unittest.mock import patch, MagicMock
    from app.providers.gemini_provider import GeminiProvider, GeminiQuotaExhaustedException
    from google.genai import errors

    provider = GeminiProvider(api_key="fake-test-key-000", model="gemini-3.5-flash-lite")

    with patch("google.genai.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client.models.generate_content.side_effect = errors.ClientError(
            code=429,
            response_json={"error": {"message": "RESOURCE_EXHAUSTED Quota exceeded for free_tier_requests"}}
        )

        with pytest.raises(GeminiQuotaExhaustedException):
            provider.generate("Test prompt for quota exhaustion")

        assert mock_client.models.generate_content.call_count == 1
        called_model = mock_client.models.generate_content.call_args.kwargs.get("model")
        assert called_model == "gemini-3.5-flash-lite"

