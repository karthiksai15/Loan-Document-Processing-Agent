from typing import List
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.db.models import UserModel
from app.api.deps import require_customer, get_current_user
from app.schemas.customer import (
    CustomerApplicationCreate,
    CustomerApplicationResponse,
    CustomerApplicationListResponse,
    CustomerDocumentItem,
    CustomerSubmitResponse,
)
from app.services import customer_service, document_service
from app.services.cross_document_verification_service import get_application_profile_data

router = APIRouter(prefix="/customer", tags=["Customer Portal"])


def _to_customer_response(db: Session, app_obj, docs) -> CustomerApplicationResponse:
    doc_items = [
        CustomerDocumentItem(
            document_id=d.document_id,
            document_type=d.document_type,
            original_filename=d.original_filename,
            file_size=d.file_size,
            uploaded_at=d.uploaded_at,
            processing_status=d.processing_status,
        )
        for d in docs
        if d.processing_status != "DELETED"
    ]

    # Load profile data for metadata (employer, education, etc.)
    try:
        profile = get_application_profile_data(db, app_obj.application_id)
    except Exception:
        profile = {}

    # Check for latest human review record for decisions & requested documents
    h_review = None
    if getattr(app_obj, "human_reviews", None) and len(app_obj.human_reviews) > 0:
        h_review = sorted(app_obj.human_reviews, key=lambda x: x.created_at or datetime.min, reverse=True)[0]

    decision = h_review.human_decision if h_review else None
    decision_reason = (h_review.decision_reason or h_review.override_reason) if h_review else None
    requested_docs = h_review.requested_documents if h_review else None
    reviewed_at = h_review.reviewed_at if h_review else None

    return CustomerApplicationResponse(
        application_id=app_obj.application_id,
        application_number=app_obj.application_number or app_obj.application_id,
        applicant_name=profile.get("applicant_name") or app_obj.applicant_name,
        loan_amount=profile.get("loan_amount") or app_obj.loan_amount,
        income_annum=profile.get("income_annum") or app_obj.income_annum,
        employer=profile.get("employer") or getattr(app_obj, "employer", None),
        loan_term=profile.get("loan_term") or getattr(app_obj, "loan_term", None),
        date_of_birth=profile.get("date_of_birth"),
        address=profile.get("address"),
        education=profile.get("education"),
        self_employed=profile.get("self_employed"),
        status=app_obj.status,
        created_at=app_obj.created_at,
        updated_at=app_obj.updated_at,
        documents_count=len(doc_items),
        documents=doc_items,
        decision=decision,
        decision_reason=decision_reason,
        requested_documents=requested_docs,
        reviewed_at=reviewed_at,
    )


@router.get(
    "/applications",
    response_model=CustomerApplicationListResponse,
    summary="List all applications owned by the authenticated customer"
)
def list_my_applications(
    current_user: UserModel = Depends(require_customer),
    db: Session = Depends(get_db)
):
    apps = customer_service.list_customer_applications(db, current_user.id)
    responses = []
    for a in apps:
        docs = document_service.list_documents_for_application(db, a.application_id)
        responses.append(_to_customer_response(db, a, docs))

    return CustomerApplicationListResponse(
        total=len(responses),
        applications=responses
    )


@router.post(
    "/applications",
    response_model=CustomerApplicationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new draft loan application with backend-generated number"
)
def create_application(
    payload: CustomerApplicationCreate,
    current_user: UserModel = Depends(require_customer),
    db: Session = Depends(get_db)
):
    app_obj = customer_service.create_customer_application(
        db=db,
        user=current_user,
        data=payload
    )
    docs = document_service.list_documents_for_application(db, app_obj.application_id)
    return _to_customer_response(db, app_obj, docs)


@router.get(
    "/applications/{application_id}",
    response_model=CustomerApplicationResponse,
    summary="Get customer application details and uploaded documents"
)
def get_my_application(
    application_id: str,
    current_user: UserModel = Depends(require_customer),
    db: Session = Depends(get_db)
):
    app_obj = customer_service.get_customer_application(db, current_user.id, application_id)
    docs = document_service.list_documents_for_application(db, app_obj.application_id)
    return _to_customer_response(db, app_obj, docs)


@router.post(
    "/applications/{application_id}/documents",
    response_model=CustomerDocumentItem,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a supporting document to the customer's draft application"
)
async def upload_application_document(
    application_id: str,
    file: UploadFile = File(...),
    document_type: str = Form(...),
    current_user: UserModel = Depends(require_customer),
    db: Session = Depends(get_db)
):
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File is missing a valid filename."
        )

    content = await file.read()

    try:
        doc_obj = customer_service.upload_customer_document(
            db=db,
            user_id=current_user.id,
            application_id=application_id,
            filename=file.filename,
            content=content,
            document_type=document_type,
            content_type=file.content_type,
        )
        return CustomerDocumentItem(
            document_id=doc_obj.document_id,
            document_type=doc_obj.document_type,
            original_filename=doc_obj.original_filename,
            file_size=doc_obj.file_size,
            uploaded_at=doc_obj.uploaded_at,
            processing_status=doc_obj.processing_status,
        )
    except document_service.DuplicateDocumentError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except document_service.FileValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.delete(
    "/applications/{application_id}/documents/{document_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete an uploaded document from customer's draft application"
)
def delete_application_document(
    application_id: str,
    document_id: str,
    current_user: UserModel = Depends(require_customer),
    db: Session = Depends(get_db)
):
    customer_service.delete_customer_document(
        db=db,
        user_id=current_user.id,
        application_id=application_id,
        document_id=document_id,
    )
    return {"status": "success", "message": f"Document '{document_id}' successfully removed."}


@router.post(
    "/applications/{application_id}/submit",
    response_model=CustomerSubmitResponse,
    status_code=status.HTTP_200_OK,
    summary="Submit loan application and start automated intelligence pipeline"
)
def submit_application(
    application_id: str,
    current_user: UserModel = Depends(require_customer),
    db: Session = Depends(get_db)
):
    app_obj = customer_service.submit_customer_application(
        db=db,
        user_id=current_user.id,
        application_id=application_id
    )
    return CustomerSubmitResponse(
        application_id=app_obj.application_id,
        application_number=app_obj.application_number or app_obj.application_id,
        status=app_obj.status,
        message="Loan application successfully submitted and queued for credit underwriting."
    )
