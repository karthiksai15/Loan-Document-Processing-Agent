import React, { useState } from 'react';
import { ShieldCheck, AlertTriangle, X, Check } from 'lucide-react';
import { useAuth } from '../../context/AuthContext';

export function DecisionModal({
  isOpen,
  onClose,
  aiRecommendation = 'OFFICER_INVESTIGATION',
  onConfirm,
  submitting,
  initialDecision = 'APPROVED',
  officerId,
}) {
  const { user } = useAuth();
  const effectiveOfficerId = officerId || user?.id;
  const [decision, setDecision] = useState(initialDecision);
  const [decisionReason, setDecisionReason] = useState('');
  const [overrideReason, setOverrideReason] = useState('');
  const [notes, setNotes] = useState('');
  const [confirmed, setConfirmed] = useState(false);
  const [validationError, setValidationError] = useState('');

  React.useEffect(() => {
    if (isOpen) {
      if (initialDecision) setDecision(initialDecision);
      setDecisionReason('');
      setOverrideReason('');
      setNotes('');
      setConfirmed(false);
      setValidationError('');
    }
  }, [isOpen, initialDecision]);

  if (!isOpen) return null;

  // Decision override logic consistent with backend Phase 18/19
  const isOverride = () => {
    const ai = (aiRecommendation || '').toUpperCase();
    const dec = (decision || '').toUpperCase();
    if (ai === 'STANDARD_REVIEW' && dec === 'APPROVED') return false;
    if (ai === 'OFFICER_INVESTIGATION' && ['OFFICER_INVESTIGATION', 'SCHEDULE_INTERVIEW', 'REQUEST_ADDITIONAL_DOCUMENTS', 'DOCUMENT_FOLLOWUP'].includes(dec)) return false;
    if (ai === 'DOCUMENT_FOLLOWUP' && ['REQUEST_ADDITIONAL_DOCUMENTS', 'DOCUMENT_FOLLOWUP'].includes(dec)) return false;
    if (ai === 'ESCALATE' && ['ESCALATED', 'ESCALATE_TO_SENIOR'].includes(dec)) return false;
    return true;
  };

  const overrideActive = isOverride();

  const handleSubmit = (e) => {
    e.preventDefault();
    setValidationError('');

    // Backend rule: Decision reason required for final actions APPROVED and REJECTED
    if (['APPROVED', 'REJECTED'].includes(decision) && !decisionReason.trim()) {
      setValidationError(`Decision reason is mandatory for final human action '${decision}'.`);
      return;
    }

    // Backend rule: Override reason required if human decision deviates from AI
    if (overrideActive && !overrideReason.trim()) {
      setValidationError('Override reason is mandatory when human decision deviates from AI recommendation.');
      return;
    }

    if (!confirmed) {
      setValidationError('Please check the confirmation box before recording final decision.');
      return;
    }

    onConfirm({
      officerId: effectiveOfficerId,
      decision,
      decisionReason: decisionReason.trim() || undefined,
      overrideReason: overrideActive ? overrideReason.trim() : undefined,
      notes: notes.trim() || undefined,
    });
  };

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <ShieldCheck size={20} color="var(--color-primary-600)" />
            <h3 style={{ fontSize: '1.05rem', fontWeight: 600 }}>
              Record Final Human Decision
            </h3>
          </div>
          <button type="button" className="btn btn-sm btn-secondary" onClick={onClose} style={{ padding: '4px' }}>
            <X size={16} />
          </button>
        </div>

        <form onSubmit={handleSubmit}>
          <div className="modal-body">
            {/* AI Recommendation Context */}
            <div style={{ background: 'var(--color-bg-subtle)', padding: '0.875rem 1rem', borderRadius: 'var(--radius-md)', border: '1px solid var(--color-border)', marginBottom: '1.25rem' }}>
              <div style={{ fontSize: '0.725rem', fontWeight: 600, color: 'var(--color-text-muted)', textTransform: 'uppercase' }}>
                AI Recommendation Reference
              </div>
              <div style={{ fontSize: '1.1rem', fontWeight: 700, color: 'var(--color-primary-700)', marginTop: '0.2rem' }}>
                {aiRecommendation.replace(/_/g, ' ')}
              </div>
              <div style={{ fontSize: '0.775rem', color: 'var(--color-text-muted)', marginTop: '0.15rem' }}>
                The AI does not decide loans. This recommendation is non-binding operational guidance.
              </div>
            </div>

            {/* Decision Select */}
            <div className="form-group">
              <label className="form-label" htmlFor="decision-select">
                Human Officer Decision:
              </label>
              <select
                id="decision-select"
                className="form-select"
                value={decision}
                onChange={(e) => {
                  setDecision(e.target.value);
                  setValidationError('');
                }}
              >
                <option value="APPROVED">APPROVED (Authorize Credit)</option>
                <option value="REJECTED">REJECTED (Decline Application)</option>
                <option value="OFFICER_INVESTIGATION">OFFICER_INVESTIGATION (In-depth manual audit)</option>
                <option value="DOCUMENT_FOLLOWUP">DOCUMENT_FOLLOWUP (Hold for documentation)</option>
                <option value="ESCALATED">ESCALATED (Refer to Senior Credit Committee)</option>
              </select>
            </div>

            {/* Override Warning & Input */}
            {overrideActive && (
              <div style={{ background: 'var(--color-warning-bg)', border: '1px solid var(--color-warning-border)', padding: '0.875rem 1rem', borderRadius: 'var(--radius-md)', marginBottom: '1.25rem' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: 'var(--color-warning-text)', fontWeight: 700, fontSize: '0.85rem', marginBottom: '0.35rem' }}>
                  <AlertTriangle size={16} />
                  <span>AI RECOMMENDATION OVERRIDE</span>
                </div>
                <p style={{ fontSize: '0.8rem', color: 'var(--color-warning-text)', marginBottom: '0.5rem' }}>
                  Your decision (<strong>{decision}</strong>) differs from the AI recommendation (<strong>{aiRecommendation}</strong>). An explicit justification is strictly mandatory for governance & audit.
                </p>
                <div className="form-group" style={{ marginBottom: 0 }}>
                  <label className="form-label" style={{ color: 'var(--color-warning-text)' }} htmlFor="override-reason-input">
                    Override Justification (Required):
                  </label>
                  <textarea
                    id="override-reason-input"
                    className="form-textarea"
                    placeholder="e.g., In-person branch verification confirmed typo on KYC application form..."
                    value={overrideReason}
                    onChange={(e) => setOverrideReason(e.target.value)}
                    rows={2}
                    required
                  />
                </div>
              </div>
            )}

            {/* Decision Reason (Mandatory for Approved and Rejected) */}
            <div className="form-group">
              <label className="form-label" htmlFor="decision-reason-input">
                Decision Rationale {['APPROVED', 'REJECTED'].includes(decision) ? '(Required for Final Decision)' : '(Optional)'}:
              </label>
              <textarea
                id="decision-reason-input"
                className="form-textarea"
                placeholder="Explain the credit basis for this decision..."
                value={decisionReason}
                onChange={(e) => setDecisionReason(e.target.value)}
                rows={2}
                required={['APPROVED', 'REJECTED'].includes(decision)}
              />
            </div>

            {/* Accompanying Notes */}
            <div className="form-group">
              <label className="form-label" htmlFor="additional-notes-input">
                Additional Internal Notes (Optional):
              </label>
              <input
                type="text"
                id="additional-notes-input"
                className="form-input"
                placeholder="Optional notes for underwriting file..."
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
              />
            </div>

            {/* Validation Error Display */}
            {validationError && (
              <div style={{ color: '#b91c1c', fontSize: '0.8rem', fontWeight: 500, marginBottom: '1rem' }}>
                {validationError}
              </div>
            )}

            {/* Safe Confirmation Checkbox */}
            <label style={{ display: 'flex', alignItems: 'flex-start', gap: '0.5rem', cursor: 'pointer', fontSize: '0.825rem', color: 'var(--color-text-primary)' }}>
              <input
                type="checkbox"
                checked={confirmed}
                onChange={(e) => setConfirmed(e.target.checked)}
                style={{ marginTop: '2px' }}
              />
              <span>
                I confirm that I am recording this credit decision as an authorized human credit officer. This action will be immutably recorded in the audit trail.
              </span>
            </label>
          </div>

          <div className="modal-footer">
            <button type="button" className="btn btn-secondary" onClick={onClose} disabled={submitting}>
              Cancel
            </button>
            <button
              type="submit"
              className={`btn ${decision === 'REJECTED' ? 'btn-danger' : 'btn-primary'}`}
              disabled={submitting}
            >
              {submitting ? 'Recording Decision...' : `Confirm Decision (${decision})`}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
