"""
LLM Review API — Phase 15 LLM Service

Endpoints:
  POST /api/v1/llm/review                                — direct structured review endpoint (Phase 15 test & evaluation)
  POST /api/v1/applications/{application_id}/llm/review  — generate review for an application
  GET  /api/v1/applications/{application_id}/llm/review  — get latest review for an application
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.llm import LLMReviewRequest, LLMDirectReviewRequest, LLMReviewResponse
from app.providers.base_llm_provider import LLMProviderUnavailableException
from app.providers.groq_provider import GroqProviderUnavailableException
from app.providers.gemini_provider import GeminiProviderUnavailableException
from app.services import llm_service

router = APIRouter(tags=["LLM Review"])


@router.post(
    "/llm/review",
    response_model=LLMReviewResponse,
    status_code=status.HTTP_200_OK,
    summary="Generate Direct LLM Review",
    description=(
        "Generates a structured LLM loan review directly from a structured review context "
        "(Phase 15 evaluation endpoint). If the LLM provider (Groq) is unavailable or unconfigured, "
        "returns HTTP 503 without fabricating a fake response."
    ),
)
def generate_direct_llm_review_endpoint(
    request: LLMDirectReviewRequest,
    db: Session = Depends(get_db),
):
    """Executes a direct structured loan review via the LLM service."""
    try:
        return llm_service.generate_direct_review(request=request, db=db)
    except (LLMProviderUnavailableException, GroqProviderUnavailableException, GeminiProviderUnavailableException) as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e),
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Direct LLM review failed: {str(e)}",
        )


@router.post(
    "/applications/{application_id}/llm/review",
    response_model=LLMReviewResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Generate LLM Review for Application",
    description=(
        "Generates an explainable LLM review for a persisted loan application. "
        "Assembles context from Phases 3–14 (application data, document evidence, "
        "validation, verification, ML risk, review intelligence, and policy RAG), "
        "calls the configured LLM provider, grounds all citations, and persists the result. "
        "Returns cached result if already generated unless force_rebuild=true."
    ),
)
def generate_llm_review_endpoint(
    application_id: str,
    request: LLMReviewRequest = LLMReviewRequest(),
    db: Session = Depends(get_db),
):
    """Triggers LLM-based explainable review for a loan application."""
    try:
        return llm_service.generate_llm_review(db, application_id, request)
    except (LLMProviderUnavailableException, GroqProviderUnavailableException, GeminiProviderUnavailableException) as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e),
        )
    except ValueError as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"LLM review generation failed: {str(e)}"
        )


@router.get(
    "/applications/{application_id}/llm/review",
    response_model=LLMReviewResponse,
    summary="Get Latest LLM Review",
    description="Retrieves the most recently generated LLM review for a loan application.",
)
def get_llm_review_endpoint(
    application_id: str,
    db: Session = Depends(get_db),
):
    """Returns the latest LLM review result for a loan application."""
    try:
        result = llm_service.get_llm_review(db, application_id)
        if result is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No LLM review found for application '{application_id}'. "
                       "Use POST to generate one first."
            )
        return result
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"LLM review retrieval failed: {str(e)}"
        )
