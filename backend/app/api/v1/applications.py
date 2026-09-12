from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.db.models import UserModel
from app.schemas.application import ApplicationCreate, ApplicationResponse, ApplicationListResponse
from app.schemas.verification import ApplicationVerificationResponse
from app.schemas.evidence import ApplicationEvidenceResponse
from app.ml.schemas import ApplicationRiskResponse
from app.schemas.review import ApplicationReviewScoreResponse
from app.services import (
    application_service,
    cross_document_verification_service,
    evidence_graph_service,
    review_score_service
)
from app.services.cross_document_verification_service import get_application_profile_data
from app.ml.predictor import predict_application_risk
from app.api.deps import check_officer_permission
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/applications", tags=["Applications"])

@router.post("", response_model=ApplicationResponse, status_code=status.HTTP_201_CREATED)
def create_application_endpoint(
    data: ApplicationCreate,
    db: Session = Depends(get_db)
):
    """Create a new loan application."""
    try:
        app_obj = application_service.create_application(db, data)
        return ApplicationResponse(
            application_id=app_obj.application_id,
            applicant_name=app_obj.applicant_name,
            loan_amount=app_obj.loan_amount,
            status=app_obj.status,
            created_at=app_obj.created_at,
            updated_at=app_obj.updated_at,
            documents_count=len(app_obj.documents)
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

from datetime import datetime
from app.schemas.application import (
    ApplicationCreate,
    ApplicationResponse,
    ApplicationListResponse,
    DashboardOverviewResponse,
    AttentionItem,
)

def _enrich_application_response(db: Session, a) -> ApplicationResponse:
    profile = get_application_profile_data(db, a.application_id)

    # Check for latest review assessment
    assessment = None
    if getattr(a, "review_assessments", None) and len(a.review_assessments) > 0:
        assessment = sorted(a.review_assessments, key=lambda x: x.created_at or datetime.min, reverse=True)[0]

    # Check for human review record
    h_review = None
    if getattr(a, "human_reviews", None) and len(a.human_reviews) > 0:
        h_review = sorted(a.human_reviews, key=lambda x: x.created_at or datetime.min, reverse=True)[0]

    review_priority = assessment.review_priority if assessment else None
    scenario = profile.get("scenario")
    hr_status = h_review.human_review_status if h_review else (
        "REQUIRED" if (review_priority in ("HIGH", "MEDIUM") or (scenario and scenario != "normal")) else "NOT_REQUIRED"
    )

    profile_name = profile.get("applicant_name")
    chosen_name = profile_name if (profile_name and not profile_name.startswith("Applicant ") and not profile_name.startswith("Synthetic ")) else (a.applicant_name or profile_name or f"Applicant {a.application_id}")
    chosen_amount = profile.get("loan_amount") if (profile.get("loan_amount") and profile.get("loan_amount") > 0) else (a.loan_amount or 0.0)

    return ApplicationResponse(
        application_id=a.application_id,
        application_number=getattr(a, "application_number", None) or a.application_id,
        user_id=getattr(a, "user_id", None),
        applicant_name=chosen_name,
        loan_amount=chosen_amount,
        status=a.status,
        created_at=a.created_at,
        updated_at=a.updated_at,
        documents_count=len([d for d in a.documents if d.processing_status != "DELETED"]),
        cibil_score=profile.get("cibil_score"),
        income_annum=profile.get("income_annum"),
        employer=profile.get("employer"),
        education=profile.get("education"),
        self_employed=profile.get("self_employed"),
        loan_term=profile.get("loan_term"),
        scenario=scenario,
        ml_risk_score=assessment.ml_risk_score if assessment else None,
        ml_risk_level=assessment.ml_risk_level if assessment else None,
        evidence_trust_score=assessment.evidence_trust_score if assessment else None,
        evidence_trust_level=assessment.evidence_trust_level if assessment else None,
        review_priority=review_priority,
        primary_reason=assessment.primary_reason if assessment else None,
        human_review_required=h_review.human_review_required if h_review else (hr_status == "REQUIRED"),
        human_review_status=hr_status,
        is_demo=getattr(a, "is_demo", False),
    )

@router.get("/dashboard/overview", response_model=DashboardOverviewResponse)
def get_dashboard_overview_endpoint(
    include_demo: bool = True,
    db: Session = Depends(get_db),
    current_officer=Depends(check_officer_permission),
):
    """Returns aggregated metrics and high-priority attention items for the loan officer dashboard."""
    apps = application_service.list_applications(db, include_demo=include_demo)
    enriched = [_enrich_application_response(db, a) for a in apps]

    total = len(enriched)
    review_required = len([a for a in enriched if a.human_review_status in ("REQUIRED", "IN_REVIEW") or a.human_review_required is True])
    high_priority = len([a for a in enriched if a.review_priority == "HIGH"])
    docs_pending = len([a for a in enriched if "missing" in (a.scenario or "").lower() or "missing" in (a.primary_reason or "").lower()])
    completed = len([a for a in enriched if a.human_review_status in ("COMPLETED", "OVERRIDDEN")])

    priority_order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
    attention_candidates = [
        a for a in enriched
        if (a.human_review_status in ("REQUIRED", "IN_REVIEW") or a.review_priority in ("HIGH", "MEDIUM") or (a.scenario and a.scenario != "normal"))
    ]
    attention_candidates.sort(key=lambda x: priority_order.get(x.review_priority or "LOW", 3))

    attention_items = [
        AttentionItem(
            application_id=a.application_id,
            applicant_name=a.applicant_name,
            loan_amount=a.loan_amount,
            ml_risk_level=a.ml_risk_level or "LOW",
            evidence_trust_level=a.evidence_trust_level or "HIGH",
            review_priority=a.review_priority or "LOW",
            human_review_status=a.human_review_status or "REQUIRED",
            primary_issue=a.primary_reason or (a.scenario.replace("_", " ").title() if a.scenario else "Standard Review"),
            scenario=a.scenario,
        )
        for a in attention_candidates[:10]
    ]

    return DashboardOverviewResponse(
        total_applications=total,
        review_required_count=review_required,
        high_priority_count=high_priority,
        documents_pending_count=docs_pending,
        completed_count=completed,
        attention_queue=attention_items,
    )

@router.post("/seed-demo-data")
def seed_demo_data_endpoint(
    db: Session = Depends(get_db),
    current_officer: UserModel = Depends(check_officer_permission),
):
    """Populates demo applications A001-A010 and runs analysis pipeline for instant review workspace testing."""
    import os
    from app.core.config import settings
    from app.services import (
        document_service,
        text_extraction_service,
        document_classification_service,
        field_extraction_service,
        document_validation_service,
        human_review_service,
    )
    from app.services.policy_service import PolicyService

    PolicyService.seed_policies(db)

    demo_ids = [f"A00{i}" if i < 10 else f"A0{i}" for i in range(1, 11)]
    seeded = []

    for app_id in demo_ids:
        app_dir = os.path.join(settings.DATA_DIR, "applicants", app_id)

        profiles_path = os.path.join(settings.DATA_DIR, "processed", "applicant_profiles.csv")
        applicant_name = f"Applicant {app_id}"
        loan_amount = 1000000.0
        income_annum = 500000.0
        if os.path.exists(profiles_path):
            try:
                import pandas as pd
                df = pd.read_csv(profiles_path)
                row = df[df["applicant_id"].astype(str).str.upper() == app_id.upper()]
                if not row.empty:
                    r = row.iloc[0]
                    if pd.notna(r.get("applicant_name")):
                        applicant_name = str(r["applicant_name"])
                    if pd.notna(r.get("loan_amount")):
                        loan_amount = float(r["loan_amount"])
                    if pd.notna(r.get("income_annum")):
                        income_annum = float(r["income_annum"])
            except Exception as e:
                logger.warning(f"Error reading profile for {app_id}: {e}")

        app_obj = application_service.get_application(db, app_id)
        if not app_obj:
            app_obj = application_service.create_application(
                db,
                ApplicationCreate(
                    application_id=app_id,
                    applicant_name=applicant_name,
                    loan_amount=loan_amount,
                ),
                is_demo=True
            )
        else:
            app_obj.applicant_name = applicant_name
            app_obj.loan_amount = loan_amount
            app_obj.is_demo = True
            db.commit()

        try:
            profile = get_application_profile_data(db, app_id)
        except Exception:
            profile = {"application_id": app_id, "applicant_name": app_obj.applicant_name, "loan_amount": app_obj.loan_amount}

        if os.path.exists(app_dir):
            for fname in sorted(os.listdir(app_dir)):
                if not (fname.endswith(".txt") or fname.endswith(".pdf")):
                    continue
                fpath = os.path.join(app_dir, fname)
                with open(fpath, "rb") as f:
                    content = f.read()

                existing_docs = document_service.list_documents_for_application(db, app_id)
                doc_obj = next((d for d in existing_docs if d.original_filename == fname), None)
                if not doc_obj:
                    try:
                        doc_obj = document_service.upload_document(
                            db=db,
                            application_id=app_id,
                            filename=fname,
                            content=content,
                            document_type="OTHER",
                            content_type="text/plain" if fname.endswith(".txt") else "application/pdf",
                        )
                    except Exception:
                        pass

                if doc_obj:
                    try:
                        text_extraction_service.extract_and_save_document_text(db, doc_obj.document_id)
                        document_classification_service.classify_document(db, doc_obj.document_id)
                        field_extraction_service.extract_and_save_fields(db, doc_obj.document_id)
                        document_validation_service.validate_and_save_document(db, doc_obj.document_id)
                    except Exception:
                        pass

        try:
            cross_document_verification_service.verify_and_save_application(db, app_id)
            evidence_graph_service.build_evidence_graph_for_application(db, app_id)
            predict_application_risk(app_id, profile)
            review_score_service.compute_and_save_review_assessment(db, app_id)
            human_review_service.evaluate_human_review_gate(app_id, db=db, force_rebuild=True)
            seeded.append(app_id)
        except Exception as e:
            logger.warning(f"Error processing pipeline for {app_id}: {e}")

    # Ensure baseline AI review exists for reference demo application A001
    try:
        from app.agent import agent_service
        existing_rev = agent_service.get_agent_review(db, "A001")
        if not existing_rev:
            agent_service.run_agent_review(db, "A001", force_rebuild=True)
    except Exception as ex:
        logger.warning(f"Note on initial agent review: {ex}")

    return {"message": "Demo data seeding complete", "seeded_applications": seeded}

@router.get("", response_model=ApplicationListResponse)
def list_applications_endpoint(
    include_demo: bool = False,
    db: Session = Depends(get_db),
    current_officer=Depends(check_officer_permission),
):
    """List all loan applications."""
    apps = application_service.list_applications(db, include_demo=include_demo)
    responses = [_enrich_application_response(db, a) for a in apps]
    return ApplicationListResponse(total=len(responses), applications=responses)

@router.get("/{application_id}", response_model=ApplicationResponse)
def get_application_endpoint(
    application_id: str,
    db: Session = Depends(get_db),
    current_officer=Depends(check_officer_permission),
):
    """Retrieve loan application details."""
    app_obj = application_service.get_application(db, application_id)
    if not app_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Application '{application_id}' not found."
        )
    return _enrich_application_response(db, app_obj)

@router.post("/{application_id}/verify", response_model=ApplicationVerificationResponse)
def verify_application_endpoint(
    application_id: str,
    db: Session = Depends(get_db),
    current_officer=Depends(check_officer_permission),
):
    """Triggers cross-document verification for a loan application."""
    try:
        app_obj = cross_document_verification_service.verify_and_save_application(db, application_id)
        payload = cross_document_verification_service.get_verification_payload(db, application_id)
        return ApplicationVerificationResponse(**payload)
    except ValueError as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Verification failed: {str(e)}")

@router.get("/{application_id}/verification", response_model=ApplicationVerificationResponse)
def get_application_verification_endpoint(
    application_id: str,
    db: Session = Depends(get_db),
    current_officer=Depends(check_officer_permission),
):
    """Retrieves cross-document verification summary and findings breakdown for a loan application."""
    try:
        payload = cross_document_verification_service.get_verification_payload(db, application_id)
        return ApplicationVerificationResponse(**payload)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Retrieval failed: {str(e)}")

@router.get("/{application_id}/evidence", response_model=ApplicationEvidenceResponse)
def get_application_evidence_endpoint(
    application_id: str,
    db: Session = Depends(get_db),
    current_officer=Depends(check_officer_permission),
):
    """Retrieves the Evidence Graph (nodes, relationships, and summary) for a loan application."""
    try:
        payload = evidence_graph_service.get_evidence_graph_payload(db, application_id)
        return ApplicationEvidenceResponse(**payload)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Evidence retrieval failed: {str(e)}")

@router.post("/{application_id}/evidence", response_model=ApplicationEvidenceResponse)
def build_application_evidence_endpoint(
    application_id: str,
    db: Session = Depends(get_db),
    current_officer=Depends(check_officer_permission),
):
    """Triggers generation/rebuilding of the Evidence Graph for a loan application."""
    try:
        evidence_graph_service.build_evidence_graph_for_application(db, application_id)
        payload = evidence_graph_service.get_evidence_graph_payload(db, application_id)
        return ApplicationEvidenceResponse(**payload)
    except ValueError as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Evidence generation failed: {str(e)}")

@router.post("/{application_id}/risk/predict", response_model=ApplicationRiskResponse)
def predict_application_risk_endpoint(
    application_id: str,
    db: Session = Depends(get_db),
    current_officer=Depends(check_officer_permission),
):
    """Predicts historical loan rejection risk for an application using trained ML champion model."""
    try:
        app_obj = application_service.get_application(db, application_id)
        if not app_obj:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Application '{application_id}' not found."
            )

        profile_data = get_application_profile_data(db, application_id)
        risk_res = predict_application_risk(application_id, profile_data)

        # Update Evidence Graph if prediction completed
        if risk_res.status == "COMPLETED":
            try:
                evidence_graph_service.build_evidence_graph_for_application(db, application_id)
            except Exception as e:
                logger.warning(f"Could not update Evidence Graph after ML prediction for '{application_id}': {e}")

        return risk_res
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"ML prediction failed: {str(e)}")

@router.post("/{application_id}/review-score", response_model=ApplicationReviewScoreResponse)
def calculate_application_review_score_endpoint(
    application_id: str,
    db: Session = Depends(get_db),
    current_officer=Depends(check_officer_permission),
):
    """Calculates or recalculates the Review Intelligence score, priority, and breakdown for a loan application."""
    try:
        review_obj = review_score_service.compute_and_save_review_assessment(db, application_id)
        payload = review_score_service.get_review_assessment_payload(db, application_id)
        return ApplicationReviewScoreResponse(**payload)
    except ValueError as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Review score calculation failed: {str(e)}")

@router.get("/{application_id}/review-score", response_model=ApplicationReviewScoreResponse)
def get_application_review_score_endpoint(
    application_id: str,
    db: Session = Depends(get_db),
    current_officer=Depends(check_officer_permission),
):
    """Retrieves the current Review Intelligence score, priority level, and factors for a loan application."""
    try:
        payload = review_score_service.get_review_assessment_payload(db, application_id)
        return ApplicationReviewScoreResponse(**payload)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Review score retrieval failed: {str(e)}")

