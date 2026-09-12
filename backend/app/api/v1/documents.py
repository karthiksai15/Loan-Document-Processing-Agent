from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.db.models import UserModel, DocumentModel, LoanApplicationModel
from app.api.deps import get_current_user
from app.schemas.document import DocumentResponse, DocumentListResponse
from app.schemas.extraction import ExtractionResponse
from app.schemas.classification import ClassificationResponse
from app.schemas.extracted_field import ExtractedFieldsResponse
from app.schemas.validation import DocumentValidationResponse
from app.services import (
    document_service,
    text_extraction_service,
    document_classification_service,
    field_extraction_service,
    document_validation_service
)

router = APIRouter(tags=["Documents"])


def authorize_document_access(
    db: Session,
    document_id: str,
    current_user: UserModel,
    require_write: bool = False
) -> DocumentModel:
    """
    Authorizes access to a document.
    - Officers and Managers can access all active documents.
    - Customers can only access documents belonging to their own applications.
    - Returns 404 if document doesn't exist, 403 if unauthorized.
    """
    doc = db.query(DocumentModel).filter(
        DocumentModel.document_id == document_id,
        DocumentModel.processing_status != "DELETED"
    ).first()
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document '{document_id}' not found."
        )

    if current_user.role in ("LOAN_OFFICER", "MANAGER"):
        return doc

    # Customer authorization: verify ownership
    is_owner = False
    if doc.uploaded_by and doc.uploaded_by == current_user.id:
        is_owner = True
    elif doc.application_id:
        app_obj = db.query(LoanApplicationModel).filter(
            (LoanApplicationModel.application_id == doc.application_id) |
            (LoanApplicationModel.application_number == doc.application_id)
        ).first()
        if app_obj and app_obj.user_id == current_user.id:
            is_owner = True
            if require_write and app_obj.status not in ["DRAFT", "PENDING"]:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Cannot delete document on application in '{app_obj.status}' status."
                )

    if not is_owner:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. You do not have permission to access this document."
        )

    return doc


def authorize_application_access(
    db: Session,
    application_id: str,
    current_user: UserModel
) -> LoanApplicationModel:
    """
    Authorizes access to an application's documents.
    - Officers and Managers can access all applications.
    - Customers can only access their own applications.
    """
    app_obj = db.query(LoanApplicationModel).filter(
        (LoanApplicationModel.application_id == application_id) |
        (LoanApplicationModel.application_number == application_id)
    ).first()
    if not app_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Application '{application_id}' not found."
        )

    if current_user.role in ("LOAN_OFFICER", "MANAGER"):
        return app_obj

    if app_obj.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. You do not have permission to access documents for this application."
        )

    return app_obj


@router.post("/applications/{application_id}/documents", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_document_endpoint(
    application_id: str,
    file: UploadFile = File(...),
    document_type: str = Form("OTHER"),
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
):
    """Upload a document (.txt or .pdf) for a loan application."""
    app_obj = authorize_application_access(db, application_id, current_user)
    if current_user.role == "CUSTOMER" and app_obj.status not in ["DRAFT", "PENDING", "ADDITIONAL_DOCUMENTS_REQUIRED"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot upload documents to application in '{app_obj.status}' status."
        )

    if not file.filename:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Uploaded file missing filename.")
        
    try:
        content = await file.read()
        doc_obj = document_service.upload_document(
            db=db,
            application_id=app_obj.application_id,
            filename=file.filename,
            content=content,
            document_type=document_type,
            content_type=file.content_type,
            uploaded_by=current_user.id
        )
        return DocumentResponse.model_validate(doc_obj)
    except document_service.DuplicateDocumentError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except document_service.FileValidationError as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Upload failed: {str(e)}")


@router.get("/applications/{application_id}/documents", response_model=DocumentListResponse)
def list_application_documents_endpoint(
    application_id: str,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
):
    """List all active documents for a loan application."""
    app_obj = authorize_application_access(db, application_id, current_user)
    docs = document_service.list_documents_for_application(db, app_obj.application_id)
    responses = [DocumentResponse.model_validate(d) for d in docs]
    return DocumentListResponse(
        application_id=application_id,
        total=len(responses),
        documents=responses
    )


@router.get("/documents/{document_id}", response_model=DocumentResponse)
def get_document_metadata_endpoint(
    document_id: str,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
):
    """Retrieve metadata for a specific document."""
    doc_obj = authorize_document_access(db, document_id, current_user)
    return DocumentResponse.model_validate(doc_obj)


@router.get("/documents/{document_id}/download")
def download_document_endpoint(
    document_id: str,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
):
    """Download the actual document file."""
    doc_obj = authorize_document_access(db, document_id, current_user)
    result = document_service.get_document_file_path(db, document_id)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document file for '{document_id}' not found or deleted."
        )
    abs_path, original_filename, mime_type = result
    return FileResponse(
        path=abs_path,
        filename=original_filename,
        media_type=mime_type
    )


@router.delete("/documents/{document_id}", status_code=status.HTTP_200_OK)
def delete_document_endpoint(
    document_id: str,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
):
    """Delete a document by ID."""
    authorize_document_access(db, document_id, current_user, require_write=True)
    success = document_service.delete_document(db, document_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document '{document_id}' not found or already deleted."
        )
    return {"message": f"Document '{document_id}' deleted successfully."}

@router.post("/documents/{document_id}/extract-text", response_model=ExtractionResponse)
def extract_document_text_endpoint(
    document_id: str,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
):
    """Triggers text extraction for a document (.txt or .pdf)."""
    authorize_document_access(db, document_id, current_user)
    try:
        doc_obj = text_extraction_service.extract_and_save_document_text(db, document_id)
        payload = text_extraction_service.get_extracted_text_payload(db, document_id)
        return ExtractionResponse(**payload)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Extraction failed: {str(e)}")

@router.get("/documents/{document_id}/text", response_model=ExtractionResponse)
def get_document_extracted_text_endpoint(
    document_id: str,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
):
    """Retrieves the extracted text content and extraction metadata for a document."""
    authorize_document_access(db, document_id, current_user)
    try:
        payload = text_extraction_service.get_extracted_text_payload(db, document_id)
        return ExtractionResponse(**payload)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Retrieval failed: {str(e)}")

@router.post("/documents/{document_id}/classify", response_model=ClassificationResponse)
def classify_document_endpoint(
    document_id: str,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
):
    """Classifies an extracted document into PAYSLIP, BANK_STATEMENT, TAX_RETURN, KYC, or OTHER."""
    authorize_document_access(db, document_id, current_user)
    try:
        doc_obj = document_classification_service.classify_document(db, document_id)
        payload = document_classification_service.get_classification_payload(db, document_id)
        return ClassificationResponse(**payload)
    except ValueError as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Classification failed: {str(e)}")

@router.get("/documents/{document_id}/classification", response_model=ClassificationResponse)
def get_document_classification_endpoint(
    document_id: str,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
):
    """Retrieves classification result and matched signal breakdown for a document."""
    authorize_document_access(db, document_id, current_user)
    try:
        payload = document_classification_service.get_classification_payload(db, document_id)
        return ClassificationResponse(**payload)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Retrieval failed: {str(e)}")

@router.post("/documents/{document_id}/extract-fields", response_model=ExtractedFieldsResponse)
def extract_document_fields_endpoint(
    document_id: str,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
):
    """Extracts structured information fields for a classified document."""
    authorize_document_access(db, document_id, current_user)
    try:
        doc_obj = field_extraction_service.extract_and_save_fields(db, document_id)
        payload = field_extraction_service.get_extracted_fields_payload(db, document_id)
        return ExtractedFieldsResponse(**payload)
    except ValueError as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Field extraction failed: {str(e)}")

@router.get("/documents/{document_id}/extracted-fields", response_model=ExtractedFieldsResponse)
def get_document_extracted_fields_endpoint(
    document_id: str,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
):
    """Retrieves extracted structured information fields and source evidence for a document."""
    authorize_document_access(db, document_id, current_user)
    try:
        payload = field_extraction_service.get_extracted_fields_payload(db, document_id)
        return ExtractedFieldsResponse(**payload)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Retrieval failed: {str(e)}")

@router.post("/documents/{document_id}/validate", response_model=DocumentValidationResponse)
def validate_document_endpoint(
    document_id: str,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
):
    """Validates an extracted document against deterministic field and structural rules."""
    authorize_document_access(db, document_id, current_user)
    try:
        doc_obj = document_validation_service.validate_and_save_document(db, document_id)
        payload = document_validation_service.get_validation_payload(db, document_id)
        return DocumentValidationResponse(**payload)
    except ValueError as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Validation failed: {str(e)}")

@router.get("/documents/{document_id}/validation", response_model=DocumentValidationResponse)
def get_document_validation_endpoint(
    document_id: str,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
):
    """Retrieves validation summary and check details for a document."""
    authorize_document_access(db, document_id, current_user)
    try:
        payload = document_validation_service.get_validation_payload(db, document_id)
        return DocumentValidationResponse(**payload)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Retrieval failed: {str(e)}")


