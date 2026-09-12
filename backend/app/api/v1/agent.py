"""
AI Review Agent API — Phase 16 AI Review Agent

Endpoints:
  POST /api/v1/applications/{application_id}/agent/review — run AI Review Agent investigation
  GET  /api/v1/applications/{application_id}/agent/review — get latest agent review result
  GET  /api/v1/applications/{application_id}/agent/trace  — get investigation trace timeline
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.agent import (
    AgentReviewRequest,
    AgentReviewResponse,
    AgentTraceResponse,
)
from app.agent import agent_service

router = APIRouter(prefix="/applications", tags=["AI Review Agent"])


@router.post(
    "/{application_id}/agent/review",
    response_model=AgentReviewResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Run AI Review Agent Investigation",
    description=(
        "Launches the autonomous AI Loan Review Agent (LangGraph) for an application. "
        "The agent investigates via read-only tools, iteratively determines required information, "
        "grounds claims in evidence/policy, guards against infinite loops and prompt injections, "
        "and produces a comprehensive explanation for the human loan officer."
    ),
)
def run_agent_review_endpoint(
    application_id: str,
    request: AgentReviewRequest = AgentReviewRequest(),
    db: Session = Depends(get_db),
):
    """Triggers autonomous AI agent review."""
    try:
        return agent_service.run_agent_review(
            db=db,
            application_id=application_id,
            force_rebuild=request.force_rebuild,
        )
    except ValueError as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Agent investigation failed: {str(e)}"
        )


@router.get(
    "/{application_id}/agent/review",
    response_model=AgentReviewResponse,
    summary="Get Latest AI Agent Review",
    description="Retrieves the most recently completed agent review for a loan application.",
)
def get_agent_review_endpoint(
    application_id: str,
    db: Session = Depends(get_db),
):
    """Returns the latest agent review result."""
    try:
        result = agent_service.get_agent_review(db, application_id)
        if result is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No agent review found for application '{application_id}'. "
                       "Use POST to run an investigation first."
            )
        return result
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Agent review retrieval failed: {str(e)}"
        )


@router.get(
    "/{application_id}/agent/trace",
    response_model=AgentTraceResponse,
    summary="Get AI Investigation Timeline / Trace",
    description="Retrieves the step-by-step investigation trace for the AI Review Agent.",
)
def get_agent_trace_endpoint(
    application_id: str,
    db: Session = Depends(get_db),
):
    """Returns the investigation trace for dashboard timeline visualization."""
    try:
        result = agent_service.get_agent_trace(db, application_id)
        if result is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No agent investigation trace found for application '{application_id}'."
            )
        return result
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Agent trace retrieval failed: {str(e)}"
        )


@router.get(
    "/{application_id}/agent/reviews",
    response_model=list[AgentReviewResponse],
    summary="Get All AI Agent Reviews (History)",
    description="Retrieves all historical agent reviews for a loan application, newest first.",
)
def get_agent_reviews_endpoint(
    application_id: str,
    db: Session = Depends(get_db),
):
    """Returns all agent reviews for review history."""
    try:
        return agent_service.get_agent_reviews(db, application_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Agent review history retrieval failed: {str(e)}"
        )
