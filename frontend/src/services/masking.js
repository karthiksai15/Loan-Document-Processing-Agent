/**
 * Sensitive Data Masking Utility (Phase 17 & Phase 20 Security & Privacy)
 * Masks Aadhaar numbers, PANs, and Bank Account numbers to protect applicant PII.
 */

export function maskAadhaar(aadhaarStr) {
  if (!aadhaarStr || typeof aadhaarStr !== 'string') return aadhaarStr;
  const digits = aadhaarStr.replace(/\D/g, '');
  if (digits.length === 12) {
    return `XXXX-XXXX-${digits.slice(-4)}`;
  }
  return aadhaarStr.replace(/\b\d{4}[ -]?\d{4}[ -]?(\d{4})\b/g, 'XXXX-XXXX-$1');
}

export function maskPAN(panStr) {
  if (!panStr || typeof panStr !== 'string') return panStr;
  const clean = panStr.trim().toUpperCase();
  if (/^[A-Z]{5}[0-9]{4}[A-Z]$/.test(clean)) {
    return `XXXXX${clean.slice(5, 9)}X`;
  }
  return panStr.replace(/\b([A-Z]{5})([0-9]{4})([A-Z])\b/g, 'XXXXX$2X');
}

export function maskBankAccount(accStr) {
  if (!accStr || typeof accStr !== 'string') return accStr;
  const digits = accStr.replace(/\D/g, '');
  if (digits.length >= 8) {
    return `XXXXXX${digits.slice(-4)}`;
  }
  return accStr;
}

export function maskDocumentText(text) {
  if (!text || typeof text !== 'string') return text;
  // Mask Aadhaar: 12 digits with optional hyphens or spaces
  let masked = text.replace(/\b\d{4}[ -]?\d{4}[ -]?(\d{4})\b/g, 'XXXX-XXXX-$1');
  // Mask PAN: 5 letters, 4 digits, 1 letter
  masked = masked.replace(/\b[A-Z]{5}([0-9]{4})[A-Z]\b/g, 'XXXXX$1X');
  // Mask Bank Account: Account/A/C followed by numbers
  masked = masked.replace(/(Account(?:\s+No\.?|\s+Number)?\s*[:#-]?\s*)(\d{6,})(\d{4})/gi, '$1XXXXXX$3');
  return masked;
}
