import os
from typing import Optional, Tuple
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.logging import logger
from app.db.models import DocumentFileModel, DocumentModel


def save_document_file(
    db: Session,
    document_id: str,
    content: bytes,
    mime_type: str,
    stored_filename: str,
    application_id: str
) -> str:
    """
    Persists document bytes both to the database (DocumentFileModel) for cloud durability
    and to the local file system cache (UPLOADS_DIR) for fast extraction.
    Returns the storage key identifier.
    """
    file_size = len(content)
    
    # 1. Persist binary in database (guaranteed survival across ephemeral container restarts)
    existing_file = db.query(DocumentFileModel).filter(
        DocumentFileModel.document_id == document_id
    ).first()
    
    if existing_file:
        existing_file.file_content = content
        existing_file.file_size = file_size
        existing_file.mime_type = mime_type
    else:
        file_record = DocumentFileModel(
            document_id=document_id,
            file_content=content,
            file_size=file_size,
            mime_type=mime_type
        )
        db.add(file_record)
    
    db.flush()

    # 2. Cache on disk for local processing
    app_dir = os.path.join(settings.UPLOADS_DIR, application_id)
    os.makedirs(app_dir, exist_ok=True)
    abs_path = os.path.join(app_dir, stored_filename)
    
    try:
        with open(abs_path, "wb") as f:
            f.write(content)
    except Exception as e:
        logger.warning(f"Could not write disk cache for document {document_id}: {e}")

    storage_key = f"db://document_files/{document_id}"
    logger.info(f"Document {document_id} ({file_size} bytes) persisted to storage with key '{storage_key}'")
    return storage_key


def get_document_bytes(
    db: Session,
    document_id: str
) -> Optional[Tuple[bytes, str]]:
    """
    Retrieves document binary content and MIME type.
    First checks disk cache; if missing (e.g. after Render restart),
    restores from the database DocumentFileModel and re-populates the disk cache.
    """
    doc_obj = db.query(DocumentModel).filter(DocumentModel.document_id == document_id).first()
    if not doc_obj:
        return None

    # Check if local file exists and is non-empty
    if doc_obj.file_path and os.path.exists(doc_obj.file_path) and os.path.getsize(doc_obj.file_path) > 0:
        try:
            with open(doc_obj.file_path, "rb") as f:
                return f.read(), doc_obj.mime_type
        except Exception as e:
            logger.warning(f"Error reading disk cache for document {document_id}: {e}")

    # Fallback to database persistence
    file_record = db.query(DocumentFileModel).filter(
        DocumentFileModel.document_id == document_id
    ).first()
    
    if not file_record or not file_record.file_content:
        return None

    content = file_record.file_content
    
    # Re-populate disk cache if path is defined
    if doc_obj.file_path:
        try:
            os.makedirs(os.path.dirname(doc_obj.file_path), exist_ok=True)
            with open(doc_obj.file_path, "wb") as f:
                f.write(content)
            logger.info(f"Restored document {document_id} to disk cache from persistent storage.")
        except Exception as e:
            logger.warning(f"Could not re-cache restored document {document_id} to disk: {e}")

    return content, file_record.mime_type


def delete_document_file(db: Session, document_id: str) -> bool:
    """
    Removes the document binary from database persistence and deletes the disk cache file.
    """
    doc_obj = db.query(DocumentModel).filter(DocumentModel.document_id == document_id).first()
    if doc_obj and doc_obj.file_path and os.path.exists(doc_obj.file_path):
        try:
            os.remove(doc_obj.file_path)
        except Exception as e:
            logger.warning(f"Error removing cached file for document {document_id}: {e}")

    file_record = db.query(DocumentFileModel).filter(
        DocumentFileModel.document_id == document_id
    ).first()
    
    if file_record:
        db.delete(file_record)
        db.commit()
        return True
    return False
