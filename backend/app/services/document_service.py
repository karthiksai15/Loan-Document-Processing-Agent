import os
import hashlib
import uuid
import mimetypes
from typing import List, Optional, Tuple
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.logging import logger
from app.db.models import DocumentModel, LoanApplicationModel
from app.services.storage_service import save_document_file, get_document_bytes, delete_document_file

class DuplicateDocumentError(ValueError):
    """Raised when an identical file checksum already exists for the application."""
    pass

class FileValidationError(ValueError):
    """Raised when file validation fails (size, extension, empty check, mime)."""
    pass

def sanitize_filename(filename: str) -> str:
    """Sanitize filename and strip path traversal attempts."""
    clean_name = os.path.basename(filename)
    clean_name = clean_name.replace("..", "").replace("/", "").replace("\\", "")
    return clean_name or "uploaded_file"

def compute_sha256(content: bytes) -> str:
    """Calculate SHA-256 checksum for binary data."""
    return hashlib.sha256(content).hexdigest()

def upload_document(
    db: Session,
    application_id: str,
    filename: str,
    content: bytes,
    document_type: str,
    content_type: Optional[str] = None,
    uploaded_by: Optional[str] = None
) -> DocumentModel:
    """
    Validates, saves, and records an uploaded document for a loan application.
    """
    # 1. Verify application exists
    app_obj = db.query(LoanApplicationModel).filter(LoanApplicationModel.application_id == application_id).first()
    if not app_obj:
        raise FileValidationError(f"Application '{application_id}' not found.")

    # 2. Validate document category / type
    doc_type_upper = document_type.upper()
    if doc_type_upper not in settings.ALLOWED_DOCUMENT_TYPES:
        allowed_str = ", ".join(settings.ALLOWED_DOCUMENT_TYPES)
        raise FileValidationError(f"Invalid document category '{document_type}'. Allowed categories: {allowed_str}")

    # 3. Sanitize filename and check extension
    safe_filename = sanitize_filename(filename)
    _, ext = os.path.splitext(safe_filename)
    ext_lower = ext.lower()
    
    if ext_lower not in settings.ALLOWED_EXTENSIONS:
        allowed_exts = ", ".join(settings.ALLOWED_EXTENSIONS)
        raise FileValidationError(f"Unsupported file extension '{ext}'. Allowed extensions: {allowed_exts}")

    # 4. Validate empty file
    file_size = len(content)
    if file_size == 0:
        raise FileValidationError("File is empty (0 bytes). Upload rejected.")

    # 5. Validate file size limit
    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    if file_size > max_bytes:
        raise FileValidationError(f"File size ({file_size} bytes) exceeds maximum limit of {settings.MAX_UPLOAD_SIZE_MB}MB.")

    # 6. Compute SHA-256 checksum and check duplicate
    checksum = compute_sha256(content)
    existing_duplicate = db.query(DocumentModel).filter(
        DocumentModel.application_id == application_id,
        DocumentModel.checksum == checksum,
        DocumentModel.processing_status != "DELETED"
    ).first()
    
    if existing_duplicate:
        logger.warning(f"Duplicate upload attempt for application '{application_id}' with checksum '{checksum}'.")
        raise DuplicateDocumentError(
            f"Duplicate document detected: An identical file ('{existing_duplicate.original_filename}') already exists for this application."
        )

    # 7. Safe local storage path generation
    doc_uuid = f"DOC-{uuid.uuid4().hex[:12]}"
    stored_filename = f"{doc_uuid}{ext_lower}"
    
    app_upload_dir = os.path.join(settings.UPLOADS_DIR, application_id)
    os.makedirs(app_upload_dir, exist_ok=True)
    
    abs_file_path = os.path.join(app_upload_dir, stored_filename)
    
    # Path traversal safety assertion
    real_upload_dir = os.path.realpath(app_upload_dir)
    real_file_path = os.path.realpath(abs_file_path)
    if not real_file_path.startswith(real_upload_dir):
        raise FileValidationError("Path traversal security violation detected.")

    # Save bytes to disk
    with open(abs_file_path, "wb") as f:
        f.write(content)

    # Resolve MIME type
    mime = content_type or mimetypes.guess_type(safe_filename)[0] or "application/octet-stream"

    # Project-relative path for clean DB metadata
    project_root = os.path.dirname(settings.DATA_DIR)
    rel_file_path = os.path.relpath(abs_file_path, project_root)

    # 7. Create DB record for parent DocumentModel first
    storage_key = f"db://document_files/{doc_uuid}"
    doc_obj = DocumentModel(
        document_id=doc_uuid,
        application_id=application_id,
        original_filename=safe_filename,
        stored_filename=stored_filename,
        file_path=rel_file_path,
        document_type=doc_type_upper,
        mime_type=mime,
        file_size=file_size,
        checksum=checksum,
        processing_status="UPLOADED",
        uploaded_by=uploaded_by,
        storage_key=storage_key
    )

    try:
        db.add(doc_obj)
        db.flush()  # Ensures documents row exists in DB transaction before child document_files insertion

        # 8. Persist document binary both to DB and disk cache
        save_document_file(
            db=db,
            document_id=doc_uuid,
            content=content,
            mime_type=mime,
            stored_filename=stored_filename,
            application_id=application_id
        )

        db.commit()
        db.refresh(doc_obj)
    except Exception:
        db.rollback()
        if os.path.exists(abs_file_path):
            try:
                os.remove(abs_file_path)
            except Exception:
                pass
        raise


    logger.info(f"Document '{doc_uuid}' ({safe_filename}) uploaded successfully for application '{application_id}'.")
    return doc_obj

def list_documents_for_application(db: Session, application_id: str) -> List[DocumentModel]:
    return db.query(DocumentModel).filter(
        DocumentModel.application_id == application_id,
        DocumentModel.processing_status != "DELETED"
    ).order_by(DocumentModel.uploaded_at.desc()).all()

def get_document_metadata(db: Session, document_id: str) -> Optional[DocumentModel]:
    return db.query(DocumentModel).filter(
        DocumentModel.document_id == document_id,
        DocumentModel.processing_status != "DELETED"
    ).first()

def get_document_file_path(db: Session, document_id: str) -> Optional[Tuple[str, str, str]]:
    """Returns (abs_file_path, original_filename, mime_type) if document exists."""
    doc = get_document_metadata(db, document_id)
    if not doc:
        return None
        
    project_root = os.path.dirname(settings.DATA_DIR)
    abs_path = os.path.join(project_root, doc.file_path)
    
    if not os.path.exists(abs_path) or os.path.getsize(abs_path) == 0:
        # Attempt recovery from persistent database storage
        recovered = get_document_bytes(db, document_id)
        if not recovered:
            logger.error(f"Document file missing on disk and persistent storage: {abs_path}")
            return None
        
    return abs_path, doc.original_filename, doc.mime_type

def delete_document(db: Session, document_id: str) -> bool:
    doc = db.query(DocumentModel).filter(DocumentModel.document_id == document_id).first()
    if not doc or doc.processing_status == "DELETED":
        return False
        
    # Mark as DELETED in DB
    doc.processing_status = "DELETED"
    db.commit()
    
    # Remove binary from persistent storage and disk cache
    delete_document_file(db, document_id)
    return True
