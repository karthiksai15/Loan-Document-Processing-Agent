/**
 * Banking & Financial Formatters
 */

export function formatINR(amount) {
  if (amount === undefined || amount === null || isNaN(amount)) return '₹0';
  const num = Number(amount);
  const abs = Math.abs(num);

  if (abs >= 10000000) { // 1 Crore
    const cr = (num / 10000000).toFixed(2);
    return `₹${cr.replace(/\.00$/, '')} Cr`;
  } else if (abs >= 100000) { // 1 Lakh
    const lakh = (num / 100000).toFixed(2);
    return `₹${lakh.replace(/\.00$/, '')} Lakh`;
  } else if (abs >= 1000) {
    const k = (num / 1000).toFixed(1);
    return `₹${k.replace(/\.0$/, '')}k`;
  }
  return `₹${num.toLocaleString('en-IN')}`;
}

export function formatFullINR(amount) {
  if (amount === undefined || amount === null || isNaN(amount)) return '₹0';
  return `₹${Number(amount).toLocaleString('en-IN')}`;
}

export function formatPercent(val, decimals = 1) {
  if (val === undefined || val === null || isNaN(val)) return '0.0%';
  const num = Number(val);
  // If val is 0.0566, format as 5.7%
  if (num > 0 && num <= 1) {
    return `${(num * 100).toFixed(decimals)}%`;
  }
  return `${num.toFixed(decimals)}%`;
}

export function formatDateTime(isoString) {
  if (!isoString) return '—';
  try {
    const d = new Date(isoString);
    if (isNaN(d.getTime())) return isoString;
    return d.toLocaleString('en-IN', {
      day: '2-digit',
      month: 'short',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  } catch {
    return isoString;
  }
}

export function formatTimeOnly(isoString) {
  if (!isoString) return '—';
  try {
    const d = new Date(isoString);
    if (isNaN(d.getTime())) return isoString;
    return d.toLocaleTimeString('en-IN', {
      hour: '2-digit',
      minute: '2-digit',
    });
  } catch {
    return isoString;
  }
}

export function getCibilCategory(score) {
  if (!score || score < 300) return { label: 'Poor', level: 'HIGH' };
  if (score >= 750) return { label: 'Excellent', level: 'LOW' };
  if (score >= 650) return { label: 'Good', level: 'MEDIUM' };
  return { label: 'Fair', level: 'HIGH' };
}

export function formatPolicySourceLabel(policy) {
  if (!policy) return 'Policy';
  if (typeof policy === 'string') {
    const p = policy.toUpperCase();
    if (p.includes('RBI')) return 'RBI';
    if (p.includes('HDFC') && !p.includes('DEMO')) return 'HDFC Bank';
    if (p.includes('DEMO')) return 'Internal Demo Policy';
    return 'Bank Policy';
  }
  const sourceLabel = (policy.source_label || '').toUpperCase();
  const authority = (policy.authority || policy.source || '').toUpperCase();
  const combined = `${sourceLabel} ${authority}`.trim();
  const isSimulated = policy.is_simulated === true || combined.includes('DEMO');
  if (combined.includes('RBI')) return 'RBI';
  if (combined.includes('HDFC') && !isSimulated) return 'HDFC Bank';
  if (isSimulated || combined.includes('DEMO')) return 'Internal Demo Policy';
  return 'Bank Policy';
}

export function formatAgentRecommendation(rec) {
  if (!rec) return 'Not Reviewed';
  const key = String(rec).toUpperCase();
  if (key === 'STANDARD_REVIEW') return 'Standard Review';
  if (key === 'DOCUMENT_FOLLOWUP') return 'Request Documents';
  if (key === 'OFFICER_INVESTIGATION') return 'Officer Investigation';
  if (key === 'ESCALATE' || key === 'ESCALATED') return 'Escalate for Officer Review';
  if (key === 'NOT_REVIEWED') return 'Not Reviewed';
  return key.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
}

export function formatDocumentType(rawType) {
  if (!rawType) return 'Document';
  const t = String(rawType).toUpperCase();
  if (t === 'KYC' || t === 'KYC_DOCUMENT') return 'KYC Document';
  if (t === 'TAX_RETURN' || t === 'ITR' || t === 'ITR_V') return 'Tax Return (ITR-V)';
  if (t === 'BANK_STATEMENT' || t === 'BANK') return 'Bank Statement';
  if (t === 'PAYSLIP' || t === 'SALARY_PAYSLIP') return 'Salary Payslip';
  if (t === 'OTHER') return 'Other Document';
  return String(rawType).toLowerCase().replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
}

export function getDocumentDisplayLabel(doc, evidenceData) {
  if (!doc) return 'Document';

  // 1. Direct classified document type from document metadata if available
  const classified = doc.classified_document_type;
  if (classified && classified.toUpperCase() !== 'OTHER') {
    return formatDocumentType(classified);
  }

  // 2. Lookup in evidence graph nodes
  if (evidenceData?.nodes) {
    const docNode = evidenceData.nodes.find(
      (n) =>
        n.node_type === 'DOCUMENT' &&
        (n.document_id === doc.document_id ||
          n.node_id === `NODE-DOC-${doc.document_id}` ||
          (doc.original_filename && n.source_reference === doc.original_filename))
    );
    if (docNode) {
      const typeMatch = docNode.value?.match(/Type:\s*([A-Z_]+)/i);
      const valType = typeMatch ? typeMatch[1] : docNode.title?.split(/[\s(]/)[0];
      if (valType && valType.toUpperCase() !== 'OTHER') {
        return formatDocumentType(valType);
      }
    }
  }

  // 3. Check document_type if not 'OTHER'
  if (doc.document_type && doc.document_type.toUpperCase() !== 'OTHER') {
    return formatDocumentType(doc.document_type);
  }

  // 4. Safe fallback to existing document_type or 'Document'
  return doc.document_type || 'Document';
}


