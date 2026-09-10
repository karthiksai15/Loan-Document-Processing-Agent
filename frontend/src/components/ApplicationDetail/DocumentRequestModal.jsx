import React, { useState } from 'react';
import { FileQuestion, X } from 'lucide-react';

const DOCUMENT_OPTIONS = [
  { id: 'TAX_RETURN', label: 'Income Tax Return (ITR-V / Acknowledgement for last 3 years)' },
  { id: 'BANK_STATEMENT', label: 'Bank Account Statement (Consecutive 6 months)' },
  { id: 'PAYSLIP', label: 'Official Payslips / Salary Slips (Last 3 months)' },
  { id: 'KYC', label: 'KYC Identity Proof (Valid Aadhaar / Passport / Voter ID)' },
  { id: 'EMPLOYMENT_PROOF', label: 'Employment Verification Letter / Business Registration' },
];

export function DocumentRequestModal({
  isOpen,
  onClose,
  onSubmit,
  submitting,
  defaultDocType = null,
}) {
  const [selectedDocs, setSelectedDocs] = useState([]);
  const [reason, setReason] = useState('');
  const [error, setError] = useState('');

  React.useEffect(() => {
    if (isOpen) {
      if (defaultDocType) {
        setSelectedDocs([defaultDocType]);
        const prettyDoc = defaultDocType.replace(/_/g, ' ');
        setReason(`Please submit official ${prettyDoc} documentation to complete application verification.`);
      } else {
        setSelectedDocs([]);
        setReason('');
      }
      setError('');
    }
  }, [isOpen, defaultDocType]);

  if (!isOpen) return null;

  const toggleDoc = (id) => {
    setSelectedDocs((prev) =>
      prev.includes(id) ? prev.filter((d) => d !== id) : [...prev, id]
    );
    setError('');
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    if (selectedDocs.length === 0) {
      setError('Please select at least one document type to request.');
      return;
    }
    if (!reason.trim()) {
      setError('Please provide a specific reason or instructions for the applicant.');
      return;
    }

    onSubmit({
      documents: selectedDocs,
      reason: reason.trim(),
    });
  };

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <FileQuestion size={20} color="var(--color-primary-600)" />
            <h3 style={{ fontSize: '1.05rem', fontWeight: 600 }}>
              Request Additional Documents
            </h3>
          </div>
          <button type="button" className="btn btn-sm btn-secondary" onClick={onClose} style={{ padding: '4px' }}>
            <X size={16} />
          </button>
        </div>

        <form onSubmit={handleSubmit}>
          <div className="modal-body">
            <p style={{ fontSize: '0.825rem', color: 'var(--color-text-secondary)', marginBottom: '1rem' }}>
              Select the documents requiring clarification or resubmission. The applicant will receive this request.
            </p>

            <div className="form-group">
              <label className="form-label">Required Documents:</label>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                {DOCUMENT_OPTIONS.map((doc) => (
                  <label
                    key={doc.id}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: '0.625rem',
                      padding: '0.5rem 0.75rem',
                      background: selectedDocs.includes(doc.id) ? 'var(--color-primary-50)' : 'var(--color-bg-subtle)',
                      border: `1px solid ${selectedDocs.includes(doc.id) ? 'var(--color-primary-600)' : 'var(--color-border)'}`,
                      borderRadius: 'var(--radius-md)',
                      cursor: 'pointer',
                      fontSize: '0.825rem',
                    }}
                  >
                    <input
                      type="checkbox"
                      checked={selectedDocs.includes(doc.id)}
                      onChange={() => toggleDoc(doc.id)}
                    />
                    <span>{doc.label}</span>
                  </label>
                ))}
              </div>
            </div>

            <div className="form-group">
              <label className="form-label" htmlFor="request-reason-input">
                Reason & Instructions for Applicant:
              </label>
              <textarea
                id="request-reason-input"
                className="form-textarea"
                placeholder="e.g., Please provide 3-year ITR to verify self-employed business revenue..."
                value={reason}
                onChange={(e) => setReason(e.target.value)}
                rows={3}
                required
              />
            </div>

            {error && (
              <div style={{ color: '#b91c1c', fontSize: '0.8rem', fontWeight: 500, marginBottom: '0.5rem' }}>
                {error}
              </div>
            )}
          </div>

          <div className="modal-footer">
            <button type="button" className="btn btn-secondary" onClick={onClose} disabled={submitting}>
              Cancel
            </button>
            <button type="submit" className="btn btn-primary" disabled={submitting}>
              {submitting ? 'Sending Request...' : 'Send Document Request'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
