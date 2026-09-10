"""
LLM Safety Service — Phase 15 & 17 Hardening

Detects prompt injection attempts, masks PII for privacy/data minimization,
and logs security audit events.

Architecture principle:
  - TRUSTED: system instructions, structured system-generated data
  - UNTRUSTED: any text extracted from uploaded documents or tool arguments
"""

import re
from typing import Tuple, List, Dict, Any
from app.core.logging import logger


# Patterns that suggest prompt injection or instruction override attempts.
# Expanded in Phase 17 to address adversarial vectors.
_INJECTION_PATTERNS: List[str] = [
    r"ignore\s+(all\s+)?(?:previous|prior)?\s*(instructions|rules|constraints|guidelines)",
    r"disregard\s+(all\s+)?(?:previous|prior)?\s*(instructions|rules|constraints|guidelines)",
    r"forget\s+(all\s+)?(?:previous|prior)?\s*(instructions|rules|constraints|guidelines)",
    r"grant\s+(?:this|the|\d+)?\s*(?:loan|amount)?\s*(?:immediately|now)",
    r"new\s+instructions?\s*:",
    r"system\s+prompt\s*:",
    r"reveal\s+(?:your\s+)?(?:system\s+prompt|instructions|initial\s+prompt)",
    r"print\s+(?:your\s+)?system\s+prompt",
    r"show\s+(?:me\s+)?(?:your\s+)?system\s+prompt",
    r"you\s+are\s+now\s+(?:a|the)\s+(?:loan\s+officer|underwriter|manager|admin)",
    r"you\s+are\s+now\s+a",
    r"act\s+as\s+(?:a\s+)?(?:different|new|unrestricted|loan\s+officer)",
    r"override\s+(?:your\s+)?(?:instructions|constraints|rules)",
    r"(?:system\s+)?override\s*:",
    r"do\s+not\s+follow\s+(?:your\s+)?instructions",
    r"jailbreak",
    r"DAN\s+mode",
    r"developer\s+mode",
    r"bypass\s+(?:all\s+)?(?:restrictions|filters|safety)",
    r"disable\s+(?:verification|checks|filters|safety|rules)",
    r"approve\s+(?:this|the)\s+(?:loan|application)\s+(?:immediately|now|regardless)",
    r"set\s+(?:loan|application)\s+(?:status|decision)\s+to\s+approved",
    r"mark\s+(?:this|the)\s+(?:loan|application)\s+as\s+approved",
    r"call\s+this\s+tool",
    r"ignore\s+(?:the\s+)?policy",
    r"use\s+another\s+applicant'?s?\s+information",
    r"</?(system|user|assistant|instruction)\s*>",  # XML/HTML injection
    r"\[\s*SYSTEM\s*\]",
    r"IMPORTANT:\s+ignore",
]

_COMPILED = [re.compile(p, re.IGNORECASE) for p in _INJECTION_PATTERNS]

# ── PII Patterns (Phase 17 Data Minimization) ─────────────────────────────────
# Mask Aadhaar (12-digit numbers), PAN (5 letters + 4 digits + 1 letter), Bank Accounts
_AADHAAR_PATTERN = re.compile(r"\b(\d{4})[\s-](\d{4})[\s-](\d{4})\b")
_PAN_PATTERN = re.compile(r"\b([A-Z]{5})(\d{4})([A-Z])\b", re.IGNORECASE)
_BANK_ACCT_PATTERN = re.compile(r"\b(\d{5,14})(\d{4})\b")


def mask_pii(text: str) -> str:
    """
    Masks sensitive personally identifiable information (PII) such as
    full Aadhaar numbers, PAN cards, and bank account numbers.
    """
    if not text:
        return text

    # Mask Aadhaar: 1234 5678 9012 -> XXXX-XXXX-9012
    masked = _AADHAAR_PATTERN.sub(r"XXXX-XXXX-\3", text)

    # Mask PAN: ABCDE1234F -> XXXXX1234F
    masked = _PAN_PATTERN.sub(r"XXXXX\2\3", masked)

    # Mask Bank account numbers (9-18 digits): 123456789012 -> XXXXXXXX9012
    masked = _BANK_ACCT_PATTERN.sub(r"XXXXXXXX\2", masked)

    return masked


def check_for_injection(text: str) -> Tuple[str, List[str]]:
    """
    Scan untrusted text for prompt injection patterns.

    Args:
        text: Raw extracted document text or tool argument (untrusted).

    Returns:
        (status, matches)
          status  — "CLEAN" or "FLAGGED"
          matches — list of matched pattern descriptions
    """
    if not text:
        return "CLEAN", []

    found: List[str] = []
    for compiled, pattern in zip(_COMPILED, _INJECTION_PATTERNS):
        if compiled.search(text):
            found.append(pattern)

    if found:
        logger.warning(f"LLM Safety: Prompt injection detected. Matched patterns: {found}")
        return "FLAGGED", found

    return "CLEAN", []


scan_prompt_injection = check_for_injection


def sanitize_untrusted_text(text: str, max_length: int = 1500) -> str:
    """
    Truncate and wrap untrusted document text in clear delimiters
    so the LLM knows it is untrusted input and not system instructions.

    This is the PRIMARY architectural injection defense.
    """
    truncated = text[:max_length] if len(text) > max_length else text
    masked = mask_pii(truncated)
    return (
        "<<<UNTRUSTED_DOCUMENT_TEXT_START>>>\n"
        + masked
        + "\n<<<UNTRUSTED_DOCUMENT_TEXT_END>>>"
    )


def log_security_event(event_type: str, details: Dict[str, Any]):
    """
    Structured security & audit logging for operational tracing.
    Excludes sensitive chain-of-thought and private document text.
    """
    sanitized_details = {k: mask_pii(str(v)) if isinstance(v, str) else v for k, v in details.items()}
    logger.warning(f"SECURITY AUDIT [{event_type}]: {sanitized_details}")
