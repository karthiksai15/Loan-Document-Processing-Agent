import os
import shutil
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, Any
import pymupdf
import pytesseract
from PIL import Image
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.logging import logger
from app.db.models import DocumentModel

@dataclass
class ExtractionResult:
    text: str
    method: str  # TEXT, PDF_TEXT, OCR
    page_count: int
    character_count: int
    success: bool
    error: Optional[str] = None

def is_tesseract_available() -> bool:
    """Check if tesseract binary is installed and accessible on system path."""
    return shutil.which("tesseract") is not None

def extract_text_from_file(abs_file_path: str, filename: str) -> ExtractionResult:
    """
    Extracts text deterministically from .txt or .pdf files.
    Prefers direct PyMuPDF text parsing for PDFs, falling back to Tesseract OCR if scanned.
    """
    if not os.path.exists(abs_file_path):
        return ExtractionResult(
            text="",
            method="UNKNOWN",
            page_count=0,
            character_count=0,
            success=False,
            error=f"Physical file missing on disk: {abs_file_path}"
        )

    _, ext = os.path.splitext(filename)
    ext_lower = ext.lower()

    # 1. Plain Text (.txt) Handling
    if ext_lower == ".txt":
        try:
            with open(abs_file_path, "rb") as f:
                raw_bytes = f.read()
            try:
                content = raw_bytes.decode("utf-8")
            except UnicodeDecodeError:
                content = raw_bytes.decode("latin-1", errors="replace")

            return ExtractionResult(
                text=content,
                method="TEXT",
                page_count=1,
                character_count=len(content),
                success=True,
                error=None
            )
        except Exception as e:
            logger.error(f"Error reading TXT file {abs_file_path}: {e}")
            return ExtractionResult(
                text="",
                method="TEXT",
                page_count=0,
                character_count=0,
                success=False,
                error=f"Failed to read TXT file: {str(e)}"
            )

    # 2. PDF Handling (.pdf)
    elif ext_lower == ".pdf":
        try:
            doc = pymupdf.open(abs_file_path)
            page_count = len(doc)
            page_texts = []
            total_chars = 0

            for page_idx in range(page_count):
                page = doc[page_idx]
                p_text = page.get_text() or ""
                trimmed = p_text.strip()
                total_chars += len(trimmed)
                page_texts.append(f"--- PAGE {page_idx + 1} ---\n{p_text}")

            full_text = "\n\n".join(page_texts)

            # Scanned PDF Detection Threshold (less than 20 total selectable chars across entire document)
            if total_chars < 20 and page_count > 0:
                if is_tesseract_available():
                    logger.info(f"PDF '{filename}' appears scanned. Triggering Tesseract OCR fallback.")
                    ocr_page_texts = []
                    ocr_total_chars = 0
                    
                    for page_idx in range(page_count):
                        page = doc[page_idx]
                        pix = page.get_pixmap(dpi=150)
                        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                        page_ocr = pytesseract.image_to_string(img) or ""
                        ocr_total_chars += len(page_ocr.strip())
                        ocr_page_texts.append(f"--- PAGE {page_idx + 1} ---\n{page_ocr}")
                        
                    ocr_full_text = "\n\n".join(ocr_page_texts)
                    return ExtractionResult(
                        text=ocr_full_text,
                        method="OCR",
                        page_count=page_count,
                        character_count=len(ocr_full_text),
                        success=True,
                        error=None
                    )
                else:
                    logger.warning(f"PDF '{filename}' appears scanned but Tesseract binary is not installed on system.")
                    return ExtractionResult(
                        text=full_text,
                        method="PDF_TEXT",
                        page_count=page_count,
                        character_count=len(full_text),
                        success=True,
                        error="Warning: Scanned PDF detected, but local Tesseract OCR binary is not installed on the system."
                    )

            # Selectable PDF text found
            return ExtractionResult(
                text=full_text,
                method="PDF_TEXT",
                page_count=page_count,
                character_count=len(full_text),
                success=True,
                error=None
            )

        except Exception as e:
            logger.error(f"Error parsing PDF file {abs_file_path}: {e}")
            return ExtractionResult(
                text="",
                method="PDF_TEXT",
                page_count=0,
                character_count=0,
                success=False,
                error=f"PDF extraction error: {str(e)}"
            )

    else:
        return ExtractionResult(
            text="",
            method="UNKNOWN",
            page_count=0,
            character_count=0,
            success=False,
            error=f"Unsupported document file extension '{ext}' for text extraction."
        )


def extract_and_save_document_text(db: Session, document_id: str) -> DocumentModel:
    """
    Service function that extracts text from a document, saves the result to data/extracted_text/,
    and records extraction metadata in the database.
    """
    doc = db.query(DocumentModel).filter(DocumentModel.document_id == document_id).first()
    if not doc or doc.processing_status == "DELETED":
        raise ValueError(f"Document '{document_id}' not found.")

    project_root = os.path.dirname(settings.DATA_DIR)
    abs_file_path = os.path.join(project_root, doc.file_path)

    # Check if already completed and text exists (idempotent)
    if doc.extraction_status == "COMPLETED":
        if doc.extracted_text:
            if doc.extracted_text_path:
                abs_text_path = os.path.join(project_root, doc.extracted_text_path)
                if not os.path.exists(abs_text_path):
                    try:
                        os.makedirs(os.path.dirname(abs_text_path), exist_ok=True)
                        with open(abs_text_path, "w", encoding="utf-8") as f:
                            f.write(doc.extracted_text)
                    except Exception as e:
                        logger.warning(f"Could not restore extracted text to disk: {e}")
            logger.info(f"Document '{document_id}' already extracted. Returning cached result.")
            return doc
        elif doc.extracted_text_path:
            abs_text_path = os.path.join(project_root, doc.extracted_text_path)
            if os.path.exists(abs_text_path):
                with open(abs_text_path, "r", encoding="utf-8", errors="replace") as f:
                    doc.extracted_text = f.read()
                db.commit()
                logger.info(f"Document '{document_id}' already extracted. Returning cached result.")
                return doc

    # Update status to PROCESSING
    doc.extraction_status = "PROCESSING"
    db.commit()

    # Perform extraction
    result = extract_text_from_file(abs_file_path, doc.original_filename)

    if result.success:
        os.makedirs(settings.EXTRACTED_TEXT_DIR, exist_ok=True)
        target_filename = f"{document_id}.txt"
        abs_target_path = os.path.join(settings.EXTRACTED_TEXT_DIR, target_filename)

        with open(abs_target_path, "w", encoding="utf-8") as f:
            f.write(result.text)

        rel_target_path = os.path.relpath(abs_target_path, project_root)

        doc.extraction_status = "COMPLETED"
        doc.extraction_method = result.method
        doc.extracted_text_path = rel_target_path
        doc.extracted_text = result.text
        doc.extracted_text_length = result.character_count
        doc.extraction_error = result.error
        doc.processed_at = datetime.utcnow()
    else:
        doc.extraction_status = "FAILED"
        doc.extraction_error = result.error

    db.commit()
    db.refresh(doc)
    return doc


def get_extracted_text_payload(db: Session, document_id: str) -> Dict[str, Any]:
    """
    Retrieves the extracted text payload and metadata for API response.
    """
    doc = db.query(DocumentModel).filter(DocumentModel.document_id == document_id).first()
    if not doc or doc.processing_status == "DELETED":
        raise ValueError(f"Document '{document_id}' not found.")

    text_content = ""
    if doc.extraction_status == "COMPLETED":
        if doc.extracted_text:
            text_content = doc.extracted_text
            # Re-materialize disk cache if missing
            if doc.extracted_text_path:
                project_root = os.path.dirname(settings.DATA_DIR)
                abs_text_path = os.path.join(project_root, doc.extracted_text_path)
                if not os.path.exists(abs_text_path):
                    try:
                        os.makedirs(os.path.dirname(abs_text_path), exist_ok=True)
                        with open(abs_text_path, "w", encoding="utf-8") as f:
                            f.write(doc.extracted_text)
                    except Exception as e:
                        logger.warning(f"Could not restore extracted text to disk: {e}")
        elif doc.extracted_text_path:
            project_root = os.path.dirname(settings.DATA_DIR)
            abs_text_path = os.path.join(project_root, doc.extracted_text_path)
            if os.path.exists(abs_text_path):
                with open(abs_text_path, "r", encoding="utf-8", errors="replace") as f:
                    text_content = f.read()
                doc.extracted_text = text_content
                db.commit()

    return {
        "document_id": doc.document_id,
        "status": doc.extraction_status,
        "method": doc.extraction_method,
        "character_count": doc.extracted_text_length,
        "text": text_content,
        "error": doc.extraction_error,
        "processed_at": doc.processed_at
    }
