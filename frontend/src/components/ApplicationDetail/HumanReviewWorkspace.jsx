import React, { useState } from 'react';
import {
  ShieldAlert,
  CheckCircle2,
  AlertTriangle,
  UserCheck,
  PlusCircle,
  FileQuestion,
  Award,
  MessageSquare,
  Clock,
} from 'lucide-react';
import { api } from '../../services/api';
import { StatusBadge } from '../Common/Badges';
import { DecisionModal } from './DecisionModal';
import { DocumentRequestModal } from './DocumentRequestModal';
import { OfficerFeedbackModal } from './OfficerFeedbackModal';
import { ErrorAlert } from '../Common/ErrorAlert';
import { formatDateTime } from '../../services/formatters';

export function HumanReviewWorkspace({ applicationId, humanReview, onRefresh }) {
  const [noteText, setNoteText] = useState('');
  const [savingNote, setSavingNote] = useState(false);
  const [actionError, setActionError] = useState('');
  const [actionSuccess, setActionSuccess] = useState('');

  // Modals
  const [decisionModalOpen, setDecisionModalOpen] = useState(false);
  const [docModalOpen, setDocModalOpen] = useState(false);
  const [feedbackModalOpen, setFeedbackModalOpen] = useState(false);
  const [submittingAction, setSubmittingAction] = useState(false);

  const status = humanReview?.human_review_status || 'REQUIRED';
  const reasons = humanReview?.reasons || [];
  const notes = humanReview?.officer_notes || [];
  const requestedDocs = humanReview?.requested_documents || [];
  const aiRecommendation = humanReview?.ai_recommendation || 'OFFICER_INVESTIGATION';

  const handleAcknowledge = async () => {
    try {
      setSubmittingAction(true);
      setActionError('');
      await api.acknowledgeReview(applicationId, 'loan_officer_001');
      setActionSuccess('Review successfully acknowledged. Status updated to IN_REVIEW.');
      setTimeout(() => setActionSuccess(''), 4000);
      if (onRefresh) onRefresh();
    } catch (err) {
      setActionError(err.message);
    } finally {
      setSubmittingAction(false);
    }
  };

  const handleAddNote = async (e) => {
    e.preventDefault();
    if (!noteText.trim()) return;

    try {
      setSavingNote(true);
      setActionError('');
      await api.addOfficerNote(applicationId, 'loan_officer_001', noteText.trim());
      setNoteText('');
      setActionSuccess('Officer note added to review record.');
      setTimeout(() => setActionSuccess(''), 4000);
      if (onRefresh) onRefresh();
    } catch (err) {
      setActionError(err.message);
    } finally {
      setSavingNote(false);
    }
  };

  const handleDocumentRequestSubmit = async (data) => {
    try {
      setSubmittingAction(true);
      setActionError('');
      await api.requestDocuments(applicationId, 'loan_officer_001', data.documents, data.reason);
      setDocModalOpen(false);
      setActionSuccess('Document request recorded and dispatched to applicant.');
      setTimeout(() => setActionSuccess(''), 4000);
      if (onRefresh) onRefresh();
    } catch (err) {
      setActionError(err.message);
    } finally {
      setSubmittingAction(false);
    }
  };

  const handleDecisionSubmit = async (payload) => {
    try {
      setSubmittingAction(true);
      setActionError('');
      await api.recordHumanDecision(applicationId, payload);
      setDecisionModalOpen(false);
      setActionSuccess(`Decision (${payload.decision}) successfully recorded by credit officer.`);
      setTimeout(() => setActionSuccess(''), 4000);
      if (onRefresh) onRefresh();
    } catch (err) {
      setActionError(err.message);
    } finally {
      setSubmittingAction(false);
    }
  };

  const handleFeedbackSubmit = async (payload) => {
    try {
      setSubmittingAction(true);
      setActionError('');
      await api.submitFeedback(applicationId, payload);
      setFeedbackModalOpen(false);
      setActionSuccess('Officer feedback recorded successfully.');
      setTimeout(() => setActionSuccess(''), 4000);
      if (onRefresh) onRefresh();
    } catch (err) {
      setActionError(err.message);
    } finally {
      setSubmittingAction(false);
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
      {/* Human Authority Guarantee Banner */}
      <div
        className="card"
        style={{
          borderLeft: '5px solid var(--color-primary-700)',
          background: 'linear-gradient(to right, #f8fafc, #ffffff)',
          padding: '1.25rem 1.5rem',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '1rem' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.25rem' }}>
              <UserCheck size={18} color="var(--color-primary-700)" />
              <span style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--color-primary-700)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                Human-in-the-Loop Authority Boundary
              </span>
            </div>
            <div style={{ fontSize: '1.25rem', fontWeight: 700, color: 'var(--color-text-primary)' }}>
              Final Loan Decision Is Made By Human Credit Officer
            </div>
            <p style={{ fontSize: '0.8rem', color: 'var(--color-text-secondary)', marginTop: '0.2rem' }}>
              The AI Review Agent provides operational triage and grounds citations. It is strictly prohibited from approving or declining applications.
            </p>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            <div style={{ textAlign: 'right' }}>
              <div style={{ fontSize: '0.7rem', color: 'var(--color-text-muted)', textTransform: 'uppercase', fontWeight: 600 }}>
                Review Gate Status
              </div>
              <StatusBadge status={status} />
            </div>
          </div>
        </div>
      </div>

      {actionError && <ErrorAlert message={actionError} />}
      {actionSuccess && (
        <div style={{ padding: '0.875rem 1rem', background: 'var(--color-success-bg)', border: '1px solid var(--color-success-border)', borderRadius: 'var(--radius-md)', color: 'var(--color-success-text)', fontSize: '0.85rem', fontWeight: 500 }}>
          {actionSuccess}
        </div>
      )}

      {/* Decision Recorded Banner if already completed */}
      {humanReview?.human_decision && (
        <div className="card" style={{ padding: '1.25rem', background: humanReview.human_decision === 'APPROVED' ? 'var(--color-success-bg)' : humanReview.human_decision === 'REJECTED' ? 'var(--color-danger-bg)' : 'var(--color-bg-subtle)', border: `1px solid ${humanReview.human_decision === 'APPROVED' ? 'var(--color-success-border)' : humanReview.human_decision === 'REJECTED' ? 'var(--color-danger-border)' : 'var(--color-border)'}` }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <Award size={18} color="var(--color-text-primary)" />
              <h4 style={{ fontSize: '0.95rem', fontWeight: 700 }}>
                Recorded Human Decision: {humanReview.human_decision}
              </h4>
            </div>
            <div style={{ display: 'flex', gap: '0.5rem' }}>
              {humanReview.override && (
                <span className="badge badge-medium">
                  AI RECOMMENDATION OVERRIDDEN
                </span>
              )}
              <StatusBadge status={humanReview.human_review_status} />
            </div>
          </div>
          <p style={{ fontSize: '0.85rem', color: 'var(--color-text-primary)', marginBottom: '0.25rem' }}>
            <strong>Decision Rationale:</strong> {humanReview.decision_reason || '—'}
          </p>
          {humanReview.override_reason && (
            <p style={{ fontSize: '0.825rem', color: 'var(--color-warning-text)' }}>
              <strong>Override Justification:</strong> {humanReview.override_reason}
            </p>
          )}
          <div style={{ fontSize: '0.75rem', color: 'var(--color-text-muted)', marginTop: '0.5rem' }}>
            Recorded by: {humanReview.reviewed_by || 'Officer Priya'} • {formatDateTime(humanReview.reviewed_at || humanReview.updated_at)}
          </div>
        </div>
      )}

      {/* Gate Reasons */}
      {reasons.length > 0 && (
        <div className="card">
          <div className="card-header">
            <h4 style={{ fontSize: '0.9rem', fontWeight: 600 }}>
              Review Trigger Reasons ({reasons.length})
            </h4>
            <span style={{ fontSize: '0.75rem', color: 'var(--color-text-muted)' }}>
              Determined by deterministic gate evaluator
            </span>
          </div>
          <div className="card-body" style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
            {reasons.map((r, i) => (
              <div
                key={i}
                style={{
                  display: 'flex',
                  alignItems: 'flex-start',
                  gap: '0.75rem',
                  padding: '0.75rem',
                  background: r.severity === 'ERROR' ? 'var(--color-danger-bg)' : 'var(--color-warning-bg)',
                  border: `1px solid ${r.severity === 'ERROR' ? 'var(--color-danger-border)' : 'var(--color-warning-border)'}`,
                  borderRadius: 'var(--radius-md)',
                }}
              >
                <AlertTriangle size={18} color={r.severity === 'ERROR' ? 'var(--color-danger-text)' : 'var(--color-warning-text)'} style={{ flexShrink: 0, marginTop: '2px' }} />
                <div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.15rem' }}>
                    <strong style={{ fontSize: '0.85rem', color: r.severity === 'ERROR' ? 'var(--color-danger-text)' : 'var(--color-warning-text)' }}>
                      {r.code}
                    </strong>
                    <span className={`badge ${r.severity === 'ERROR' ? 'badge-high' : 'badge-medium'}`} style={{ fontSize: '0.65rem' }}>
                      {r.severity}
                    </span>
                  </div>
                  <div style={{ fontSize: '0.825rem', color: r.severity === 'ERROR' ? 'var(--color-danger-text)' : 'var(--color-warning-text)' }}>
                    {r.description}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Action Bar */}
      <div className="card" style={{ padding: '1.25rem' }}>
        <h4 style={{ fontSize: '0.9rem', fontWeight: 600, marginBottom: '0.75rem' }}>
          Underwriting Actions
        </h4>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.75rem' }}>
          {status === 'REQUIRED' && (
            <button
              type="button"
              className="btn btn-secondary"
              onClick={handleAcknowledge}
              disabled={submittingAction}
            >
              <UserCheck size={16} />
              <span>Acknowledge Review (Start Investigation)</span>
            </button>
          )}

          <button
            type="button"
            className="btn btn-primary"
            onClick={() => setDecisionModalOpen(true)}
            disabled={submittingAction}
          >
            <Award size={16} />
            <span>Record Final Human Decision</span>
          </button>

          <button
            type="button"
            className="btn btn-secondary"
            onClick={() => setDocModalOpen(true)}
            disabled={submittingAction}
          >
            <FileQuestion size={16} />
            <span>Request Documents</span>
          </button>

          <button
            type="button"
            className="btn btn-secondary"
            onClick={() => setFeedbackModalOpen(true)}
            disabled={submittingAction}
          >
            <MessageSquare size={16} />
            <span>Submit Officer Feedback</span>
          </button>
        </div>
      </div>

      {/* Officer Notes Form & History */}
      <div className="card">
        <div className="card-header">
          <h4 style={{ fontSize: '0.9rem', fontWeight: 600 }}>
            Underwriting Notes & Observations ({notes.length})
          </h4>
        </div>
        <div className="card-body">
          {/* Note Input */}
          <form onSubmit={handleAddNote} style={{ marginBottom: '1.25rem' }}>
            <div style={{ display: 'flex', gap: '0.5rem' }}>
              <input
                type="text"
                className="form-input"
                placeholder="Add timestamped loan officer observation..."
                value={noteText}
                onChange={(e) => setNoteText(e.target.value)}
                style={{ flex: 1 }}
              />
              <button type="submit" className="btn btn-primary" disabled={savingNote || !noteText.trim()}>
                <PlusCircle size={16} />
                <span>{savingNote ? 'Saving...' : 'Add Note'}</span>
              </button>
            </div>
          </form>

          {/* Notes History */}
          {notes.length > 0 ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.625rem' }}>
              {notes.map((n, i) => (
                <div key={i} style={{ padding: '0.75rem', background: 'var(--color-bg-subtle)', borderRadius: 'var(--radius-md)', border: '1px solid var(--color-border)' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.25rem', fontSize: '0.75rem' }}>
                    <strong style={{ color: 'var(--color-text-primary)' }}>{n.officer_id}</strong>
                    <span style={{ color: 'var(--color-text-muted)', display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
                      <Clock size={12} />
                      {formatDateTime(n.timestamp)}
                    </span>
                  </div>
                  <p style={{ fontSize: '0.85rem', color: 'var(--color-text-secondary)', lineHeight: 1.4 }}>
                    {n.text}
                  </p>
                </div>
              ))}
            </div>
          ) : (
            <div style={{ fontSize: '0.825rem', color: 'var(--color-text-muted)', fontStyle: 'italic' }}>
              No officer notes added yet.
            </div>
          )}
        </div>
      </div>

      {/* Requested Documents History */}
      {requestedDocs.length > 0 && (
        <div className="card">
          <div className="card-header">
            <h4 style={{ fontSize: '0.9rem', fontWeight: 600 }}>
              Requested Document Follow-ups ({requestedDocs.length})
            </h4>
          </div>
          <div className="card-body">
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.625rem' }}>
              {requestedDocs.map((req, i) => (
                <div key={i} style={{ padding: '0.75rem', background: 'var(--color-bg-subtle)', borderRadius: 'var(--radius-md)', border: '1px solid var(--color-border)', fontSize: '0.825rem' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.25rem' }}>
                    <strong style={{ color: 'var(--color-primary-700)' }}>{req.doc_type}</strong>
                    <span style={{ color: 'var(--color-text-muted)', fontSize: '0.75rem' }}>
                      {formatDateTime(req.timestamp)}
                    </span>
                  </div>
                  <p style={{ color: 'var(--color-text-secondary)' }}>
                    <strong>Reason:</strong> {req.reason}
                  </p>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Modals */}
      <DecisionModal
        isOpen={decisionModalOpen}
        onClose={() => setDecisionModalOpen(false)}
        aiRecommendation={aiRecommendation}
        onConfirm={handleDecisionSubmit}
        submitting={submittingAction}
      />

      <DocumentRequestModal
        isOpen={docModalOpen}
        onClose={() => setDocModalOpen(false)}
        onSubmit={handleDocumentRequestSubmit}
        submitting={submittingAction}
      />

      <OfficerFeedbackModal
        isOpen={feedbackModalOpen}
        onClose={() => setFeedbackModalOpen(false)}
        onSubmit={handleFeedbackSubmit}
        submitting={submittingAction}
      />
    </div>
  );
}
