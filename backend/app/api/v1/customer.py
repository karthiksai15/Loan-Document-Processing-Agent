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

router = APIRouter(prefix="/customer", tags=["Customer Portal"])


def _to_customer_response(app_obj, docs) -> CustomerApplicationResponse:
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
    return CustomerApplicationResponse(
        application_id=app_obj.application_id,
        application_number=app_obj.application_number or app_obj.application_id,
        applicant_name=app_obj.applicant_name,
        loan_amount=app_obj.loan_amount,
        income_annum=app_obj.income_annum,
        employer=getattr(app_obj, "employer", None),
        status=app_obj.status,
        created_at=app_obj.created_at,
        updated_at=app_obj.updated_at,
        documents_count=len(doc_items),
        documents=doc_items,
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
        responses.append(_to_customer_response(a, docs))

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
    return _to_customer_response(app_obj, docs)


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
    return _to_customer_response(app_obj, docs)


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
