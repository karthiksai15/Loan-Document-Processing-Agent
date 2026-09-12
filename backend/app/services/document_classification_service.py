import os
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.logging import logger
from app.db.models import DocumentModel

@dataclass
class ClassificationResult:
    document_type: str  # PAYSLIP, BANK_STATEMENT, TAX_RETURN, KYC, OTHER
    confidence: float
    method: str  # KEYWORD_RULES
    matched_signals: List[str]
    scores: Dict[str, float]
    error: Optional[str] = None

DOCUMENT_RULES: Dict[str, Dict[str, Any]] = {
    "PAYSLIP": {
        "strong": [
            "payslip", "pay slip", "monthly gross salary", "monthly net salary",
            "gross salary", "net salary", "pay period", "employee id", "basic salary"
        ],
        "medium": [
            "employee name", "employer", "salary", "earnings", "deductions",
            "employment status", "annual declared income", "allowance", "take home pay"
        ],
        "weights": {"strong": 3.0, "medium": 1.0}
    },
    "BANK_STATEMENT": {
        "strong": [
            "bank statement", "account number", "statement period", "total monthly credits",
            "average monthly balance", "monthly salary credit", "opening balance", "closing balance"
        ],
        "medium": [
            "account holder", "transaction", "credit", "debit", "balance",
            "withdrawal", "deposit", "ledger balance"
        ],
        "weights": {"strong": 3.0, "medium": 1.0}
    },
    "TAX_RETURN": {
        "strong": [
            "income tax return", "tax return", "taxpayer name", "tax year",
            "declared annual income", "assessment year", "gross total income", "tax paid"
        ],
        "medium": [
            "taxable income", "annual income", "income tax", "form 16", "itr",
            "acknowledgement number", "tax refund"
        ],
        "weights": {"strong": 3.0, "medium": 1.0}
    },
    "KYC": {
        "strong": [
            "kyc / identity document", "identity document", "kyc", "synthetic id number",
            "dummy_kyc_id", "identity number", "aadhaar", "passport", "pan number", "voter id"
        ],
        "medium": [
            "full name", "date of birth", "dob", "address", "residency",
            "identity proof", "nationality", "gender"
        ],
        "weights": {"strong": 3.0, "medium": 1.0}
    }
}

def normalize_text(text: str) -> str:
    """Normalize text by lowercasing and replacing punctuation/extra whitespace."""
    if not text:
        return ""
    text_clean = text.lower()
    text_clean = re.sub(r'[\-_/\\:]', ' ', text_clean)
    text_clean = re.sub(r'\s+', ' ', text_clean).strip()
    return text_clean

def classify_text(text: str) -> ClassificationResult:
    """
    Classifies raw extracted text into PAYSLIP, BANK_STATEMENT, TAX_RETURN, KYC, or OTHER
    using a deterministic weighted keyword scoring engine.
    """
    norm_text = normalize_text(text)
    
    empty_scores = {cat: 0.0 for cat in ["PAYSLIP", "BANK_STATEMENT", "TAX_RETURN", "KYC"]}
    if not norm_text:
        return ClassificationResult(
            document_type="OTHER",
            confidence=0.0,
            method="KEYWORD_RULES",
            matched_signals=[],
            scores=empty_scores,
            error=None
        )

    category_scores: Dict[str, float] = {}
    matched_signals_by_cat: Dict[str, List[str]] = {}

    for cat, rules in DOCUMENT_RULES.items():
        cat_score = 0.0
        matched = []
        
        # Check strong signals
        for term in rules["strong"]:
            if term in norm_text:
                cat_score += rules["weights"]["strong"]
                matched.append(term)
                
        # Check medium signals
        for term in rules["medium"]:
            if term in norm_text:
                cat_score += rules["weights"]["medium"]
                matched.append(term)
                
        category_scores[cat] = cat_score
        matched_signals_by_cat[cat] = matched

    # Sort categories by score descending
    sorted_cats = sorted(category_scores.items(), key=lambda x: x[1], reverse=True)
    top_cat, top_score = sorted_cats[0]
    second_cat, second_score = sorted_cats[1]

    MIN_SCORE_THRESHOLD = 2.0
    
    # 1. Low Score Check -> OTHER
    if top_score < MIN_SCORE_THRESHOLD:
        return ClassificationResult(
            document_type="OTHER",
            confidence=round(min(0.35, top_score / 5.0), 2),
            method="KEYWORD_RULES",
            matched_signals=[],
            scores=category_scores,
            error=None
        )

    # 2. Ambiguity Guard: if top two categories are too close (diff < 0.5 and both > 0)
    if (top_score - second_score) < 0.5 and second_score > 0:
        logger.info(f"Ambiguous signals detected between {top_cat} ({top_score}) and {second_cat} ({second_score}). Flagging as OTHER.")
        return ClassificationResult(
            document_type="OTHER",
            confidence=0.30,
            method="KEYWORD_RULES",
            matched_signals=matched_signals_by_cat[top_cat] + matched_signals_by_cat[second_cat],
            scores=category_scores,
            error="Ambiguous keyword signals detected across multiple document types."
        )

    # 3. Confident Category Match
    # Heuristic confidence calculation formula bounded between 0.50 and 0.95
    heuristic_conf = min(0.95, round(0.50 + (top_score / (top_score + 4.0)) * 0.45, 2))

    return ClassificationResult(
        document_type=top_cat,
        confidence=heuristic_conf,
        method="KEYWORD_RULES",
        matched_signals=matched_signals_by_cat[top_cat],
        scores=category_scores,
        error=None
    )


def classify_document(db: Session, document_id: str) -> DocumentModel:
    """
    Service function that retrieves extracted text for a document, runs document classification,
    and persists classification metadata to the database.
    """
    doc = db.query(DocumentModel).filter(DocumentModel.document_id == document_id).first()
    if not doc or doc.processing_status == "DELETED":
        raise ValueError(f"Document '{document_id}' not found.")

    if doc.extraction_status != "COMPLETED" or (not doc.extracted_text_path and not doc.extracted_text):
        raise ValueError(f"Text for document '{document_id}' has not been extracted yet. Please execute /extract-text prior to classification.")

    # Check if already classified (idempotent)
    if doc.classification_status == "COMPLETED" and doc.classified_document_type:
        logger.info(f"Document '{document_id}' already classified. Returning cached classification.")
        return doc

    doc.classification_status = "CLASSIFYING"
    db.commit()

    text_content = ""
    if doc.extracted_text:
        text_content = doc.extracted_text
    elif doc.extracted_text_path:
        project_root = os.path.dirname(settings.DATA_DIR)
        abs_text_path = os.path.join(project_root, doc.extracted_text_path)
        if os.path.exists(abs_text_path):
            with open(abs_text_path, "r", encoding="utf-8", errors="replace") as f:
                text_content = f.read()

    result = classify_text(text_content)

    doc.classified_document_type = result.document_type
    doc.classification_confidence = result.confidence
    doc.classification_method = result.method
    doc.classification_status = "COMPLETED"
    doc.classification_signals = {
        "matched_signals": result.matched_signals,
        "scores": result.scores
    }
    doc.classification_error = result.error
    doc.classified_at = datetime.utcnow()

    db.commit()
    db.refresh(doc)
    return doc


def get_classification_payload(db: Session, document_id: str) -> Dict[str, Any]:
    """Retrieves classification response payload for API client."""
    doc = db.query(DocumentModel).filter(DocumentModel.document_id == document_id).first()
    if not doc or doc.processing_status == "DELETED":
        raise ValueError(f"Document '{document_id}' not found.")

    signals = doc.classification_signals or {}
    matched = signals.get("matched_signals", [])
    scores = signals.get("scores", {})

    return {
        "document_id": doc.document_id,
        "classified_document_type": doc.classified_document_type or "OTHER",
        "confidence": doc.classification_confidence or 0.0,
        "classification_method": doc.classification_method or "KEYWORD_RULES",
        "status": doc.classification_status,
        "matched_signals": matched,
        "scores": scores,
        "error": doc.classification_error,
        "classified_at": doc.classified_at
    }
