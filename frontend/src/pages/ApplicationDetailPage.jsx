import React, { useEffect, useState, useCallback } from 'react';
import { useParams, Link } from 'react-router-dom';
import {
  ChevronLeft,
  UserRound,
  ChartNoAxesColumnIncreasing,
  Files,
  FileText,
  Landmark,
  ReceiptText,
  BadgeCheck,
  CircleAlert,
  Sparkles,
  Layers,
  UserCheck,
  CheckCircle2,
  AlertTriangle,
  ChevronRight,
  BookOpen,
  GitCompareArrows,
  History,
  Check,
  X,
  ArrowUpRight,
  PlusCircle,
  MessageSquare,
  FileQuestion,
  HelpCircle,
} from 'lucide-react';
import { api } from '../services/api';
import { useAuth } from '../context/AuthContext';
import { formatINR, formatPercent, formatDateTime, formatAgentRecommendation } from '../services/formatters';

// Modals
import { DecisionModal } from '../components/ApplicationDetail/DecisionModal';
import { DocumentRequestModal } from '../components/ApplicationDetail/DocumentRequestModal';
import { OfficerFeedbackModal } from '../components/ApplicationDetail/OfficerFeedbackModal';

// Right-Side Floating Drawers
import { RightSideDrawer } from '../components/ApplicationDetail/Drawers/RightSideDrawer';
import { DocumentViewerDrawer } from '../components/ApplicationDetail/Drawers/DocumentViewerDrawer';
import { AIReviewDrawer } from '../components/ApplicationDetail/Drawers/AIReviewDrawer';
import { SourcesDrawer } from '../components/ApplicationDetail/Drawers/SourcesDrawer';
import { PolicyBasisDrawer } from '../components/ApplicationDetail/Drawers/PolicyBasisDrawer';
import { CrossVerificationDrawer } from '../components/ApplicationDetail/Drawers/CrossVerificationDrawer';
import { EvidenceDrawer } from '../components/ApplicationDetail/Drawers/EvidenceDrawer';
import { AIInvestigationDrawer } from '../components/ApplicationDetail/Drawers/AIInvestigationDrawer';
import { DecisionHistoryDrawer } from '../components/ApplicationDetail/Drawers/DecisionHistoryDrawer';

import { LoadingState } from '../components/Common/LoadingState';
import { ErrorAlert } from '../components/Common/ErrorAlert';

export function ApplicationDetailPage() {
  const { applicationId } = useParams();

  const [application, setApplication] = useState(null);
  const [reviewScore, setReviewScore] = useState(null);
  const [verificationData, setVerificationData] = useState(null);
  const [evidenceData, setEvidenceData] = useState(null);
  const [documents, setDocuments] = useState([]);
  const [agentReview, setAgentReview] = useState(null);
  const [humanReview, setHumanReview] = useState(null);

  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState(null);

  // Right-Side Drawer State
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [drawerView, setDrawerView] = useState('document'); // 'document' | 'ai_review' | 'sources' | 'policy_basis' | 'verification' | 'evidence' | 'ai_investigation' | 'decision_history'
  const [selectedDoc, setSelectedDoc] = useState(null);

  // Action Modals State
  const [decisionModalOpen, setDecisionModalOpen] = useState(false);
  const [presetDecision, setPresetDecision] = useState('APPROVED');
  const [docModalOpen, setDocModalOpen] = useState(false);
  const [defaultDocType, setDefaultDocType] = useState('TAX_RETURN');
  const [feedbackModalOpen, setFeedbackModalOpen] = useState(false);
  const [noteModalOpen, setNoteModalOpen] = useState(false);
  const [noteInput, setNoteInput] = useState('');
  const [actionSuccess, setActionSuccess] = useState('');
  const [actionError, setActionError] = useState('');
  const [submittingAction, setSubmittingAction] = useState(false);

  const { user } = useAuth();
  const activeOfficerId = user?.id;

  const loadApplicationData = useCallback(async (isInitial = false) => {
    if (!applicationId) return;

    if (isInitial) setLoading(true);
    else setRefreshing(true);
    setError(null);

    try {
      const appData = await api.getApplication(applicationId);
      setApplication(appData);

      const [
        reviewScoreRes,
        verifRes,
        evidenceRes,
        docsRes,
        agentRes,
        humanRes,
      ] = await Promise.allSettled([
        api.getReviewScore(applicationId),
        api.getVerification(applicationId),
        api.getEvidence(applicationId),
        api.listDocuments(applicationId),
        api.getAgentReview(applicationId),
        api.getHumanReview(applicationId),
      ]);

      if (reviewScoreRes.status === 'fulfilled') setReviewScore(reviewScoreRes.value);
      if (verifRes.status === 'fulfilled') setVerificationData(verifRes.value);
      if (evidenceRes.status === 'fulfilled') setEvidenceData(evidenceRes.value);
      if (docsRes.status === 'fulfilled') setDocuments(docsRes.value?.documents || []);
      if (agentRes.status === 'fulfilled') setAgentReview(agentRes.value);
      if (humanRes.status === 'fulfilled') setHumanReview(humanRes.value);
    } catch (err) {
      setError(err.message);
    } finally {
      if (isInitial) setLoading(false);
      else setRefreshing(false);
    }
  }, [applicationId]);

  useEffect(() => {
    loadApplicationData(true);
  }, [loadApplicationData]);

  // Helper for activeDrawer state compatibility if needed
  const setActiveDrawer = (drawer) => {
    if (!drawer) {
      setDrawerOpen(false);
    } else {
      setDrawerView(drawer);
      setDrawerOpen(true);
    }
  };

  // Handle ESC key to close any active drawer
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'Escape') {
        setActiveDrawer(null);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  // Drawer Openers
  const openDocumentDrawer = (doc) => {
    setSelectedDoc(doc);
    setDrawerView('document');
    setDrawerOpen(true);
  };

  const openDrawer = (view) => {
    setDrawerView(view);
    setDrawerOpen(true);
  };

  const closeDrawer = () => {
    setDrawerOpen(false);
  };

  // Action Handlers
  const handleOpenDecision = (decision) => {
    setPresetDecision(decision);
    setDecisionModalOpen(true);
  };

  const handleOpenDocRequest = (docType = 'TAX_RETURN') => {
    setDefaultDocType(docType);
    setDocModalOpen(true);
  };

  const handleAcknowledge = async () => {
    try {
      setSubmittingAction(true);
      setActionError('');
      await api.acknowledgeReview(applicationId, activeOfficerId);
      setActionSuccess('Review successfully acknowledged. Status updated to IN_REVIEW.');
      setTimeout(() => setActionSuccess(''), 4000);
      loadApplicationData(false);
    } catch (err) {
      setActionError(err.message);
    } finally {
      setSubmittingAction(false);
    }
  };

  const handleAddNoteSubmit = async (e) => {
    e.preventDefault();
    if (!noteInput.trim()) return;
    try {
      setSubmittingAction(true);
      setActionError('');
      await api.addOfficerNote(applicationId, activeOfficerId, noteInput.trim());
      setNoteModalOpen(false);
      setNoteInput('');
      setActionSuccess('Officer note added to review audit trail.');
      setTimeout(() => setActionSuccess(''), 4000);
      loadApplicationData(false);
    } catch (err) {
      setActionError(err.message);
    } finally {
      setSubmittingAction(false);
    }
  };

  const handleDocumentRequestSubmit = async (data) => {
    try {
      setSubmittingAction(true);
      setActionError('');
      await api.requestDocuments(applicationId, activeOfficerId, data.documents, data.reason);
      setDocModalOpen(false);
      setActionSuccess(`Document request dispatched for ${data.documents.join(', ')}.`);
      setTimeout(() => setActionSuccess(''), 4000);
      loadApplicationData(false);
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
      await api.recordHumanDecision(applicationId, {
        ...payload,
        officerId: payload.officerId || activeOfficerId,
      });
      setDecisionModalOpen(false);
      setActionSuccess(`Final decision '${payload.decision}' successfully recorded in audit log.`);
      setTimeout(() => setActionSuccess(''), 4000);
      loadApplicationData(false);
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
      await api.submitFeedback(applicationId, {
        ...payload,
        officerId: payload.officerId || activeOfficerId,
      });
      setFeedbackModalOpen(false);
      setActionSuccess('Officer feedback recorded for underwriting improvement.');
      setTimeout(() => setActionSuccess(''), 4000);
      loadApplicationData(false);
    } catch (err) {
      setActionError(err.message);
    } finally {
      setSubmittingAction(false);
    }
  };

  if (loading) {
    return <LoadingState message="Loading loan application workspace..." />;
  }

  if (error || !application) {
    return (
      <div className="content-container" style={{ padding: '2rem' }}>
        <ErrorAlert
          message={error || `Application '${applicationId}' not found.`}
          onRetry={() => loadApplicationData(true)}
        />
        <div style={{ marginTop: '1rem' }}>
          <Link to="/applications" className="btn btn-secondary btn-sm">
            ← Return to Applications List
          </Link>
        </div>
      </div>
    );
  }

  // Derived values from real data
  const mlRiskScore = application.ml_risk_score !== undefined && application.ml_risk_score !== null
    ? application.ml_risk_score
    : (reviewScore?.risk_breakdown?.ml_rejection_probability ?? 0.05);

  const mlLevel = application.ml_risk_level || (mlRiskScore >= 0.7 ? 'HIGH' : mlRiskScore >= 0.3 ? 'MEDIUM' : 'LOW');

  const evidenceTrustScore = application.evidence_trust_score !== undefined && application.evidence_trust_score !== null
    ? application.evidence_trust_score
    : (reviewScore?.risk_breakdown?.evidence_trust_score ?? (reviewScore?.review_score ? Math.round(reviewScore.review_score * 0.7) : 45));

  const evidenceLevel = application.evidence_trust_level || (evidenceTrustScore >= 80 ? 'HIGH' : evidenceTrustScore >= 60 ? 'MEDIUM' : 'LOW');

  // Review Priority: 0 - 100
  const priorityScore = reviewScore?.review_score !== undefined && reviewScore?.review_score !== null
    ? Math.round(reviewScore.review_score)
    : 68;

  const priorityLevel = reviewScore?.priority_level || (priorityScore >= 70 ? 'HIGH' : priorityScore >= 40 ? 'MEDIUM' : 'LOW');

  // Verification findings & Attention Items
  const findings = verificationData?.findings || [];
  const mismatches = findings.filter((f) => f.result === 'MISMATCH');
  const identityMismatch = findings.find((f) => f.verification_type === 'IDENTITY_COMPARISON' && f.result === 'MISMATCH');
  const incomeMismatch = findings.find((f) => (f.verification_type === 'INCOME_COMPARISON' || f.verification_type === 'SALARY_COMPARISON') && f.result === 'MISMATCH');

  // Expected 4 document types in standard underwriting
  const expectedDocs = [
    { type: 'PAYSLIP', label: 'Payslip', icon: FileText },
    { type: 'BANK_STATEMENT', label: 'Bank Statement', icon: Landmark },
    { type: 'TAX_RETURN', label: 'Tax Return', icon: ReceiptText },
    { type: 'KYC', label: 'KYC Document', icon: BadgeCheck },
  ];

  // Map uploaded documents by type
  const docTypeMap = {};
  documents.forEach((d) => {
    const t = (d.document_type || '').toUpperCase();
    const f = (d.original_filename || '').toLowerCase();
    if (t === 'PAYSLIP' || f.includes('payslip')) docTypeMap['PAYSLIP'] = d;
    else if (t === 'BANK_STATEMENT' || f.includes('bank')) docTypeMap['BANK_STATEMENT'] = d;
    else if (t === 'TAX_RETURN' || f.includes('tax')) docTypeMap['TAX_RETURN'] = d;
    else if (t === 'KYC' || f.includes('kyc') || f.includes('aadhaar')) docTypeMap['KYC'] = d;
    else docTypeMap[t] = d;
  });

  // Derive primary missing document if any
  const missingDocType = !docTypeMap['TAX_RETURN']
    ? 'TAX_RETURN'
    : (!docTypeMap['BANK_STATEMENT']
        ? 'BANK_STATEMENT'
        : (!docTypeMap['PAYSLIP']
            ? 'PAYSLIP'
            : (!docTypeMap['KYC'] ? 'KYC' : 'TAX_RETURN')));

  // Human review status & override detection
  const hrStatus = humanReview?.human_review_status || application.human_review_status || 'REQUIRED';
  const humanDecision = humanReview?.decision || null;
  const aiRecommendation =
    agentReview?.final_review?.recommended_next_step ||
    agentReview?.recommended_next_step ||
    agentReview?.recommendation ||
    'STANDARD_REVIEW';

  const isOverride = humanDecision && (
    (humanDecision === 'APPROVED' && (aiRecommendation === 'OFFICER_INVESTIGATION' || aiRecommendation === 'ESCALATE')) ||
    (humanDecision === 'REJECTED' && aiRecommendation === 'STANDARD_REVIEW')
  );

  return (
    <div className="app-review-page">
      {/* Toast Notifications */}
      {actionSuccess && (
        <div style={{ padding: '0.75rem 1rem', background: '#f0fdf4', border: '1px solid #bbf7d0', borderRadius: 'var(--radius-md)', color: '#166534', fontSize: '0.85rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <CheckCircle2 size={16} color="#16a34a" />
          <span>{actionSuccess}</span>
        </div>
      )}
      {actionError && (
        <div style={{ padding: '0.75rem 1rem', background: '#fef2f2', border: '1px solid #fecaca', borderRadius: 'var(--radius-md)', color: '#991b1b', fontSize: '0.85rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <AlertTriangle size={16} color="#dc2626" />
          <span>{actionError}</span>
        </div>
      )}

      {/* Header & Breadcrumb */}
      <div className="app-review-header">
        <Link to="/applications" className="back-link">
          <ChevronLeft size={16} />
          <span>Back to Applications</span>
        </Link>

        <div className="app-review-title-row">
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.85rem' }}>
            <h1 style={{ fontSize: '1.6rem', fontWeight: 800, color: 'var(--color-text-primary)', margin: 0, letterSpacing: '-0.02em' }}>
              Application Review
            </h1>
            <span className="badge" style={{ background: '#fff1f2', color: '#e11d48', border: '1px solid #fecdd3', fontSize: '0.75rem', padding: '0.2rem 0.65rem' }}>
              ● Requires Review
            </span>
          </div>

          <div className="app-review-meta-right">
            <div>
              <span style={{ color: 'var(--color-text-muted)' }}>Application ID: </span>
              <strong style={{ fontFamily: 'var(--font-mono)', color: 'var(--color-text-primary)' }}>{application.application_id}</strong>
            </div>
            <div>
              <span style={{ color: 'var(--color-text-muted)' }}>Submitted on: </span>
              <strong style={{ color: 'var(--color-text-primary)' }}>{formatDateTime(application.created_at)}</strong>
            </div>
          </div>
        </div>
        <p style={{ fontSize: '0.85rem', color: 'var(--color-text-muted)', margin: 0 }}>
          Review application details, documents and AI analysis
        </p>
      </div>

      {/* Override Alert Notice (if human decision deviates from AI) */}
      {isOverride && (
        <div style={{ padding: '0.75rem 1rem', background: '#fffbeb', border: '1px solid #fde68a', borderRadius: 'var(--radius-md)', display: 'flex', alignItems: 'center', gap: '0.6rem', fontSize: '0.8rem', color: '#92400e' }}>
          <AlertTriangle size={16} color="#d97706" style={{ flexShrink: 0 }} />
          <span>
            <strong>Human Decision Override:</strong> Officer recorded <strong>{humanDecision}</strong> while AI advised <strong>{aiRecommendation}</strong>. Justification logged in audit trail.
          </span>
        </div>
      )}

      {/* =========================================================================
          ROW 1: APPLICANT INFORMATION | REVIEW SUMMARY | DOCUMENTS
          ========================================================================= */}
      <div className="app-review-row-1">
        {/* 1. Applicant Information Card */}
        <div className="review-card">
          <div className="review-card-header">
            <div className="review-card-title">
              <UserRound size={17} color="#2563eb" />
              <span>Applicant Information</span>
            </div>
          </div>

          <div style={{ marginBottom: '1rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <span style={{ fontSize: '1.25rem', fontWeight: 800, color: 'var(--color-text-primary)' }}>
                {application.applicant_name}
              </span>
              <span className="badge badge-info" style={{ fontSize: '0.7rem', padding: '0.15rem 0.5rem' }}>
                {application.application_id}
              </span>
            </div>
          </div>

          <div className="applicant-info-grid">
            <div>
              <div className="info-item-label">Loan Amount</div>
              <div className="info-item-value">{formatINR(application.loan_amount)}</div>
            </div>
            <div>
              <div className="info-item-label">Annual Income</div>
              <div className="info-item-value">{formatINR(application.income_annum)}</div>
            </div>
            <div>
              <div className="info-item-label">CIBIL Score</div>
              <div className="info-item-value" style={{ color: (application.cibil_score || 0) < 600 ? '#b91c1c' : 'var(--color-text-primary)' }}>
                {application.cibil_score || '—'}
              </div>
            </div>
            <div>
              <div className="info-item-label">Employment Type</div>
              <div className="info-item-value">{application.self_employed === 'Yes' ? 'Self-Employed' : 'Salaried'}</div>
            </div>
            <div style={{ gridColumn: 'span 2' }}>
              <div className="info-item-label">Employer</div>
              <div className="info-item-value" style={{ fontWeight: 600 }}>{application.employer || '—'}</div>
            </div>
          </div>
        </div>

        {/* 2. Review Summary Card (Risk Score, Evidence Quality, Review Priority) */}
        <div className="review-card">
          <div className="review-card-header">
            <div className="review-card-title">
              <ChartNoAxesColumnIncreasing size={17} color="#2563eb" />
              <span>Review Summary</span>
            </div>
          </div>

          <div className="review-summary-cols">
            {/* Risk Score */}
            <div className="summary-metric-box">
              <div>
                <div className="summary-metric-title">
                  <span>ML Risk Score</span>
                  <HelpCircle size={13} color="var(--color-text-muted)" title="Statistical ML model estimation of historical rejection risk" />
                </div>
                <div className="summary-metric-num">
                  {formatPercent(mlRiskScore)}
                </div>
                <div className="summary-metric-subtext">
                  Statistical model rejection risk
                </div>
              </div>
              <span className={`badge ${mlLevel === 'LOW' ? 'badge-low' : mlLevel === 'MEDIUM' ? 'badge-medium' : 'badge-high'}`} style={{ width: 'fit-content', fontSize: '0.725rem' }}>
                {mlLevel}
              </span>
            </div>

            {/* Evidence Quality */}
            <div className="summary-metric-box" style={{ borderLeft: '1px solid var(--color-border)', borderRight: '1px solid var(--color-border)', paddingLeft: '0.75rem', paddingRight: '0.75rem' }}>
              <div>
                <div className="summary-metric-title">
                  <span>Evidence Trust Score</span>
                  <HelpCircle size={13} color="var(--color-text-muted)" title="Document completeness and cross-document field consistency (0-100)" />
                </div>
                <div className="summary-metric-num">
                  {Math.round(evidenceTrustScore)}
                </div>
                <div style={{ fontSize: '0.7rem', color: 'var(--color-text-muted)', fontWeight: 500 }}>
                  out of 100
                </div>
                <div className="summary-metric-subtext">
                  Completeness & consistency
                </div>
              </div>
              <span className={`badge ${evidenceLevel === 'HIGH' ? 'badge-low' : evidenceLevel === 'MEDIUM' ? 'badge-medium' : 'badge-high'}`} style={{ width: 'fit-content', fontSize: '0.725rem' }}>
                {evidenceLevel}
              </span>
            </div>

            {/* Review Priority */}
            <div className="summary-metric-box" style={{ paddingLeft: '0.5rem' }}>
              <div>
                <div className="summary-metric-title">
                  <span>Review Priority</span>
                  <HelpCircle size={13} color="var(--color-text-muted)" title="Operational urgency ranking for underwriter attention (0-100)" />
                </div>
                <div className="summary-metric-num">
                  {priorityScore}
                </div>
                <div style={{ fontSize: '0.7rem', color: 'var(--color-text-muted)', fontWeight: 500 }}>
                  out of 100
                </div>
                <div className="summary-metric-subtext">
                  Operational review urgency
                </div>
              </div>
              <span className={`badge ${priorityLevel === 'HIGH' ? 'badge-high' : priorityLevel === 'MEDIUM' ? 'badge-medium' : 'badge-low'}`} style={{ width: 'fit-content', fontSize: '0.725rem' }}>
                {priorityLevel}
              </span>
            </div>
          </div>
        </div>

        {/* 3. Documents Card */}
        <div className="review-card">
          <div className="review-card-header">
            <div className="review-card-title">
              <Files size={17} color="#2563eb" />
              <span>Documents</span>
            </div>
            <button
              type="button"
              className="doc-view-link"
              onClick={() => openDrawer('sources')}
              style={{ fontSize: '0.75rem' }}
            >
              <span>View All</span>
              <ChevronRight size={13} />
            </button>
          </div>

          <div className="doc-list-simple">
            {expectedDocs.map((item) => {
              const uploadedDoc = docTypeMap[item.type];
              const IconComponent = item.icon;

              // Check if doc has verification mismatch
              const hasDocMismatch = uploadedDoc && findings.some(
                (f) => (f.comparison_document_id === uploadedDoc.document_id || f.source_document_id === uploadedDoc.document_id) && f.result === 'MISMATCH'
              );

              return (
                <div key={item.type} className="doc-row-simple">
                  <div className="doc-row-left">
                    <IconComponent size={16} color="var(--color-primary-600)" />
                    <span>{item.label}</span>
                  </div>

                  <div className="doc-row-right">
                    {uploadedDoc ? (
                      <>
                        {hasDocMismatch ? (
                          <AlertTriangle size={15} color="#d97706" title="Discrepancy detected" />
                        ) : (
                          <CheckCircle2 size={15} color="#16a34a" title="Available & verified" />
                        )}
                        <button
                          type="button"
                          className="doc-view-link"
                          onClick={() => openDocumentDrawer(uploadedDoc)}
                        >
                          <span>View</span>
                          <ChevronRight size={13} />
                        </button>
                      </>
                    ) : (
                      <>
                        <span style={{ display: 'inline-flex', alignItems: 'center', gap: '0.35rem', fontSize: '0.75rem', color: '#94a3b8' }}>
                          <span style={{ width: '6px', height: '6px', borderRadius: '50%', background: '#cbd5e1' }} />
                          Missing
                        </span>
                        <button
                          type="button"
                          className="doc-view-link"
                          style={{ color: '#d97706' }}
                          onClick={() => handleOpenDocRequest(item.type)}
                        >
                          Request
                        </button>
                      </>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* =========================================================================
          ROW 2: WHAT NEEDS ATTENTION | AI REVIEW
          ========================================================================= */}
      <div className="app-review-row-2">
        {/* 1. What Needs Attention Card */}
        <div className="review-card">
          <div className="review-card-header">
            <div className="review-card-title" style={{ color: mismatches.length > 0 ? '#92400e' : '#1e3a8a' }}>
              <CircleAlert size={17} color={mismatches.length > 0 ? '#d97706' : '#2563eb'} />
              <span>What Needs Attention</span>
            </div>
            {mismatches.length > 0 && (
              <button
                type="button"
                className="doc-view-link"
                onClick={() => openDrawer('verification')}
                style={{ fontSize: '0.75rem' }}
              >
                <span>View Details</span>
                <ChevronRight size={13} />
              </button>
            )}
          </div>

          {identityMismatch ? (
            <div className="attention-card-wrap">
              <div className="attention-row-header">
                <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: '#f59e0b', flexShrink: 0 }} />
                <span>Identity information does not match</span>
              </div>

              <div className="attention-details-grid">
                <span style={{ color: 'var(--color-text-muted)' }}>Application name</span>
                <strong style={{ color: 'var(--color-text-primary)' }}>{String(identityMismatch.value_a)}</strong>

                <span style={{ color: 'var(--color-text-muted)' }}>KYC name</span>
                <strong style={{ color: '#b91c1c' }}>{String(identityMismatch.value_b)}</strong>
              </div>

              <div className="attention-helper-text">
                Please verify the applicant's identity before proceeding.
              </div>
            </div>
          ) : incomeMismatch ? (
            <div className="attention-card-wrap">
              <div className="attention-row-header">
                <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: '#f59e0b', flexShrink: 0 }} />
                <span>Income information differs between documents</span>
              </div>
              <div className="attention-details-grid">
                <span style={{ color: 'var(--color-text-muted)' }}>{incomeMismatch.source_a}</span>
                <strong style={{ color: 'var(--color-text-primary)' }}>{String(incomeMismatch.value_a)}</strong>

                <span style={{ color: 'var(--color-text-muted)' }}>{incomeMismatch.source_b}</span>
                <strong style={{ color: '#b91c1c' }}>{String(incomeMismatch.value_b)}</strong>
              </div>
              <div className="attention-helper-text">
                Verify declared income against salary credits before sanctioning.
              </div>
            </div>
          ) : !docTypeMap['TAX_RETURN'] ? (
            <div className="attention-card-wrap" style={{ background: '#fffbeb', borderColor: '#fde68a' }}>
              <div className="attention-row-header">
                <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: '#f59e0b', flexShrink: 0 }} />
                <span>Missing document</span>
              </div>
              <p style={{ fontSize: '0.8rem', color: 'var(--color-text-primary)', margin: '0 0 0.5rem 0' }}>
                Tax Return (ITR-V) is missing from this loan application.
              </p>
              <div className="attention-helper-text">
                Request applicant's latest income tax acknowledgement.
              </div>
            </div>
          ) : !docTypeMap['BANK_STATEMENT'] ? (
            <div className="attention-card-wrap" style={{ background: '#fffbeb', borderColor: '#fde68a' }}>
              <div className="attention-row-header">
                <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: '#f59e0b', flexShrink: 0 }} />
                <span>Missing document</span>
              </div>
              <p style={{ fontSize: '0.8rem', color: 'var(--color-text-primary)', margin: '0 0 0.5rem 0' }}>
                Operative Bank Statement is missing from this loan application.
              </p>
              <div className="attention-helper-text">
                Request applicant's last 6 months bank statement.
              </div>
            </div>
          ) : (application.cibil_score || 0) < 500 && mlRiskScore >= 0.8 ? (
            <div className="attention-card-wrap" style={{ background: '#fef2f2', borderColor: '#fecaca' }}>
              <div className="attention-row-header" style={{ color: '#991b1b' }}>
                <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: '#ef4444', flexShrink: 0 }} />
                <span>Credit bureau risk</span>
              </div>
              <p style={{ fontSize: '0.8rem', color: 'var(--color-text-primary)', margin: '0 0 0.4rem 0' }}>
                Applicant CIBIL score is {application.cibil_score} with elevated historical rejection probability ({formatPercent(mlRiskScore)}).
              </p>
              <div style={{ fontSize: '0.75rem', color: '#7f1d1d' }}>
                Mandatory credit committee escalation required under bank credit norms.
              </div>
            </div>
          ) : (
            <div style={{ padding: '0.85rem 1rem', background: '#f0fdf4', border: '1px solid #bbf7d0', borderRadius: 'var(--radius-md)', display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
              <CheckCircle2 size={18} color="#16a34a" style={{ flexShrink: 0 }} />
              <div>
                <div style={{ fontSize: '0.85rem', fontWeight: 600, color: '#166534' }}>All Clear</div>
                <div style={{ fontSize: '0.75rem', color: '#15803d' }}>
                  No active discrepancies or critical issues flagged. All submitted documentation passes verification rules.
                </div>
              </div>
            </div>
          )}
        </div>

        {/* 2. AI Review Section Card */}
        {(() => {
          const hasAiReview = Boolean(
            agentReview && (agentReview.final_review || agentReview.investigation_status)
          );
          const rawRec =
            agentReview?.final_review?.recommended_next_step ||
            agentReview?.recommended_next_step ||
            agentReview?.recommendation ||
            null;
          const recLabel = formatAgentRecommendation(rawRec);
          const summaryText =
            agentReview?.final_review?.executive_summary ||
            agentReview?.executive_summary ||
            '';
          const rawConf =
            agentReview?.final_review?.confidence ?? agentReview?.confidence;
          const confPct =
            rawConf !== undefined && rawConf !== null
              ? Math.round(rawConf <= 1 ? rawConf * 100 : rawConf)
              : null;
          const grounding =
            agentReview?.final_review?.grounding_status ||
            agentReview?.grounding_status ||
            'GROUNDED';

          let badgeClass = 'badge-neutral';
          const upperRec = String(rawRec || '').toUpperCase();
          if (upperRec === 'STANDARD_REVIEW') badgeClass = 'badge-low';
          else if (
            upperRec === 'OFFICER_INVESTIGATION' ||
            upperRec === 'DOCUMENT_FOLLOWUP'
          )
            badgeClass = 'badge-medium';
          else if (upperRec === 'ESCALATE' || upperRec === 'ESCALATED')
            badgeClass = 'badge-high';

          return (
            <div className="review-card">
              <div className="review-card-header">
                <div className="review-card-title">
                  <Sparkles size={17} color="#2563eb" />
                  <span>AI Review</span>
                </div>
                {hasAiReview ? (
                  <span
                    className={`badge ${badgeClass}`}
                    style={{ fontSize: '0.7rem', padding: '0.15rem 0.5rem' }}
                  >
                    ● {recLabel}
                  </span>
                ) : (
                  <span
                    className="badge badge-neutral"
                    style={{ fontSize: '0.7rem', padding: '0.15rem 0.5rem' }}
                  >
                    Not Reviewed
                  </span>
                )}
              </div>

              <p
                style={{
                  fontSize: '0.825rem',
                  color: 'var(--color-text-secondary)',
                  lineHeight: 1.5,
                  marginBottom: '0.75rem',
                }}
              >
                {hasAiReview && summaryText
                  ? (summaryText.length > 140
                      ? `${summaryText.slice(0, 137)}...`
                      : summaryText)
                  : 'AI can analyze the application documents, verify information and provide an explainable underwriting recommendation.'}
              </p>

              {hasAiReview && confPct !== null && (
                <div
                  style={{
                    fontSize: '0.75rem',
                    color: 'var(--color-text-muted)',
                    marginBottom: '1rem',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '0.75rem',
                  }}
                >
                  <span>
                    Confidence:{' '}
                    <strong style={{ color: 'var(--color-text-primary)' }}>
                      {confPct}%
                    </strong>
                  </span>
                  <span>•</span>
                  <span>
                    Grounding:{' '}
                    <strong style={{ color: '#16a34a' }}>{grounding}</strong>
                  </span>
                </div>
              )}

              <div
                style={{
                  marginTop: 'auto',
                  display: 'flex',
                  justifyContent: 'center',
                }}
              >
                <button
                  type="button"
                  className="btn btn-primary"
                  onClick={() => openDrawer('ai_review')}
                  style={{
                    padding: '0.55rem 1.75rem',
                    borderRadius: 'var(--radius-full)',
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: '0.5rem',
                    fontSize: '0.875rem',
                  }}
                >
                  <Sparkles size={16} />
                  <span>{hasAiReview ? 'View AI Review' : 'Run AI Review'}</span>
                </button>
              </div>
            </div>
          );
        })()}
      </div>

      {/* =========================================================================
          ROW 3: MORE DETAILS | HUMAN REVIEW
          ========================================================================= */}
      <div className="app-review-row-3">
        {/* 1. More Details Card (6-item vertical list) */}
        <div className="review-card">
          <div className="review-card-header">
            <div>
              <div className="review-card-title">
                <Layers size={17} color="#2563eb" />
                <span>More Details</span>
              </div>
              <p style={{ fontSize: '0.75rem', color: 'var(--color-text-muted)', margin: '0.2rem 0 0 0' }}>
                Explore detailed analysis, evidence, policies and decision history
              </p>
            </div>
          </div>

          <div className="more-details-list">
            <div className="more-details-row" onClick={() => openDrawer('sources')}>
              <div className="more-details-row-left">
                <Files size={16} color="var(--color-primary-600)" />
                <div className="more-details-row-text">
                  <span className="more-details-row-title">Sources</span>
                  <span className="more-details-row-desc">Verified evidence & policy origin data</span>
                </div>
              </div>
              <ChevronRight size={15} color="var(--color-text-muted)" />
            </div>

            <div className="more-details-row" onClick={() => openDrawer('policy_basis')}>
              <div className="more-details-row-left">
                <BookOpen size={16} color="var(--color-primary-600)" />
                <div className="more-details-row-text">
                  <span className="more-details-row-title">Policy Basis</span>
                  <span className="more-details-row-desc">Applicable bank and regulatory policies</span>
                </div>
              </div>
              <ChevronRight size={15} color="var(--color-text-muted)" />
            </div>

            <div className="more-details-row" onClick={() => openDrawer('verification')}>
              <div className="more-details-row-left">
                <GitCompareArrows size={16} color="var(--color-primary-600)" />
                <div className="more-details-row-text">
                  <span className="more-details-row-title">Cross-Document Verification</span>
                  <span className="more-details-row-desc">Detailed verification checks and results</span>
                </div>
              </div>
              <ChevronRight size={15} color="var(--color-text-muted)" />
            </div>

            <div className="more-details-row" onClick={() => openDrawer('evidence')}>
              <div className="more-details-row-left">
                <Layers size={16} color="var(--color-primary-600)" />
                <div className="more-details-row-text">
                  <span className="more-details-row-title">Evidence</span>
                  <span className="more-details-row-desc">Evidence graph and extracted information</span>
                </div>
              </div>
              <ChevronRight size={15} color="var(--color-text-muted)" />
            </div>

            <div className="more-details-row" onClick={() => openDrawer('ai_investigation')}>
              <div className="more-details-row-left">
                <Sparkles size={16} color="var(--color-primary-600)" />
                <div className="more-details-row-text">
                  <span className="more-details-row-title">AI Investigation</span>
                  <span className="more-details-row-desc">Agent reasoning, analysis and trace</span>
                </div>
              </div>
              <ChevronRight size={15} color="var(--color-text-muted)" />
            </div>

            <div className="more-details-row" onClick={() => openDrawer('decision_history')}>
              <div className="more-details-row-left">
                <History size={16} color="var(--color-primary-600)" />
                <div className="more-details-row-text">
                  <span className="more-details-row-title">Decision History</span>
                  <span className="more-details-row-desc">Past decisions, notes and officer actions</span>
                </div>
              </div>
              <ChevronRight size={15} color="var(--color-text-muted)" />
            </div>
          </div>
        </div>

        {/* 2. Human Review Card */}
        <div className="review-card">
          <div className="review-card-header">
            <div>
              <div className="review-card-title">
                <UserCheck size={17} color="#2563eb" />
                <span>Human Review</span>
              </div>
              <p style={{ fontSize: '0.75rem', color: 'var(--color-text-muted)', margin: '0.2rem 0 0 0' }}>
                AI provides recommendations. Final decision is made by the loan officer.
              </p>
            </div>
          </div>

          {user?.role === 'CUSTOMER' ? (
            <div
              style={{
                padding: '0.875rem 1rem',
                background: 'var(--color-bg-subtle)',
                borderRadius: 'var(--radius-md)',
                fontSize: '0.8rem',
                color: 'var(--color-text-secondary)',
                textAlign: 'center',
                border: '1px solid var(--color-border)',
              }}
            >
              Underwriting review actions and credit decisions are restricted to bank loan officers.
            </div>
          ) : (
            <>
              {/* Action Buttons Row */}
              <div className="human-review-actions-row">
                <button
                  type="button"
                  className="btn btn-secondary btn-sm"
                  onClick={handleAcknowledge}
                  disabled={submittingAction}
                  style={{ fontSize: '0.75rem', padding: '0.45rem 0.35rem' }}
                  title="Acknowledge review"
                >
                  <Check size={14} />
                  <span>{submittingAction ? 'Acknowledging...' : 'Acknowledge'}</span>
                </button>
                <button
                  type="button"
                  className="btn btn-secondary btn-sm"
                  onClick={() => setNoteModalOpen(true)}
                  disabled={submittingAction}
                  style={{ fontSize: '0.75rem', padding: '0.45rem 0.35rem' }}
                  title="Add underwriter note"
                >
                  <FileText size={14} />
                  <span>Add Note</span>
                </button>
                <button
                  type="button"
                  className="btn btn-secondary btn-sm"
                  onClick={() => handleOpenDocRequest(missingDocType)}
                  disabled={submittingAction}
                  style={{ fontSize: '0.75rem', padding: '0.45rem 0.35rem' }}
                  title="Request missing documents"
                >
                  <FileQuestion size={14} />
                  <span>Request Docs</span>
                </button>
                <button
                  type="button"
                  className="btn btn-secondary btn-sm"
                  onClick={() => setFeedbackModalOpen(true)}
                  disabled={submittingAction}
                  style={{ fontSize: '0.75rem', padding: '0.45rem 0.35rem' }}
                  title="Submit officer feedback"
                >
                  <MessageSquare size={14} />
                  <span>Feedback</span>
                </button>
              </div>

              {/* Final Decision Buttons Row */}
              <div className="human-review-decisions-row">
                <button
                  type="button"
                  className="btn btn-success"
                  onClick={() => handleOpenDecision('APPROVED')}
                  disabled={submittingAction}
                  style={{ padding: '0.65rem 0.5rem', fontWeight: 600, fontSize: '0.875rem' }}
                >
                  <Check size={16} />
                  <span>Approve</span>
                </button>
                <button
                  type="button"
                  className="btn btn-danger"
                  onClick={() => handleOpenDecision('REJECTED')}
                  disabled={submittingAction}
                  style={{ padding: '0.65rem 0.5rem', fontWeight: 600, fontSize: '0.875rem' }}
                >
                  <X size={16} />
                  <span>Reject</span>
                </button>
                <button
                  type="button"
                  className="btn btn-secondary"
                  onClick={() => handleOpenDecision('ESCALATED')}
                  disabled={submittingAction}
                  style={{ padding: '0.65rem 0.5rem', fontWeight: 600, fontSize: '0.875rem' }}
                >
                  <ArrowUpRight size={16} />
                  <span>Escalate</span>
                </button>
              </div>
            </>
          )}
        </div>
      </div>

      {/* =========================================================================
          REUSABLE RIGHT-SIDE FLOATING DRAWER CONTAINER
          ========================================================================= */}
      <RightSideDrawer
        isOpen={drawerOpen}
        onClose={closeDrawer}
        title={
          drawerView === 'document'
            ? selectedDoc?.original_filename || 'Document Viewer'
            : drawerView === 'ai_review'
            ? 'AI Review'
            : drawerView === 'sources'
            ? 'Sources'
            : drawerView === 'policy_basis'
            ? 'Policy Basis'
            : drawerView === 'verification'
            ? 'Cross-Document Verification'
            : drawerView === 'evidence'
            ? 'Evidence'
            : drawerView === 'ai_investigation'
            ? 'AI Investigation'
            : 'Decision History'
        }
        subtitle={
          drawerView === 'sources'
            ? 'Verified evidence & policy origin data'
            : drawerView === 'policy_basis'
            ? 'Applicable bank and regulatory policies'
            : drawerView === 'verification'
            ? 'Detailed verification checks and results'
            : drawerView === 'evidence'
            ? 'Evidence graph and extracted information'
            : drawerView === 'ai_investigation'
            ? 'Agent reasoning, analysis and trace'
            : drawerView === 'decision_history'
            ? 'Past decisions, notes and officer actions'
            : null
        }
        icon={
          drawerView === 'document'
            ? FileText
            : drawerView === 'ai_review'
            ? Sparkles
            : drawerView === 'sources'
            ? Files
            : drawerView === 'policy_basis'
            ? BookOpen
            : drawerView === 'verification'
            ? GitCompareArrows
            : drawerView === 'evidence'
            ? Layers
            : drawerView === 'ai_investigation'
            ? Sparkles
            : History
        }
      >
        {drawerView === 'document' && (
          <DocumentViewerDrawer
            document={selectedDoc}
            application={application}
            verificationFindings={findings}
          />
        )}
        {drawerView === 'ai_review' && (
          <AIReviewDrawer
            applicationId={applicationId}
            agentReview={agentReview}
            onReviewUpdated={(updated) => {
              setAgentReview(updated);
              loadApplicationData(false);
            }}
          />
        )}
        {drawerView === 'sources' && (
          <SourcesDrawer
            applicationId={applicationId}
            agentReview={agentReview}
            application={application}
            documents={documents}
            onSelectDocument={openDocumentDrawer}
          />
        )}
        {drawerView === 'policy_basis' && (
          <PolicyBasisDrawer applicationId={applicationId} agentReview={agentReview} />
        )}
        {drawerView === 'verification' && (
          <CrossVerificationDrawer verificationData={verificationData} />
        )}
        {drawerView === 'evidence' && (
          <EvidenceDrawer
            applicationId={applicationId}
            application={application}
            documents={documents}
            evidenceData={evidenceData}
            verificationData={verificationData}
            onSelectDocument={openDocumentDrawer}
          />
        )}
        {drawerView === 'ai_investigation' && (
          <AIInvestigationDrawer applicationId={applicationId} agentReview={agentReview} />
        )}
        {drawerView === 'decision_history' && (
          <DecisionHistoryDrawer applicationId={applicationId} />
        )}
      </RightSideDrawer>

      {/* =========================================================================
          MODALS
          ========================================================================= */}
      <DecisionModal
        isOpen={decisionModalOpen}
        initialDecision={presetDecision}
        aiRecommendation={aiRecommendation}
        onClose={() => setDecisionModalOpen(false)}
        onConfirm={handleDecisionSubmit}
        submitting={submittingAction}
        officerId={activeOfficerId}
      />

      <DocumentRequestModal
        isOpen={docModalOpen}
        defaultDocType={defaultDocType}
        onClose={() => setDocModalOpen(false)}
        onSubmit={handleDocumentRequestSubmit}
        submitting={submittingAction}
      />

      <OfficerFeedbackModal
        isOpen={feedbackModalOpen}
        onClose={() => setFeedbackModalOpen(false)}
        onSubmit={handleFeedbackSubmit}
        submitting={submittingAction}
        officerId={activeOfficerId}
      />

      {/* Add Note Modal */}
      {noteModalOpen && (
        <div className="modal-backdrop" onClick={() => setNoteModalOpen(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()} style={{ maxWidth: '480px' }}>
            <div className="modal-header">
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <FileText size={20} color="var(--color-primary-600)" />
                <h3 style={{ fontSize: '1.05rem', fontWeight: 600 }}>Add Loan Officer Note</h3>
              </div>
              <button type="button" className="btn btn-sm btn-secondary" onClick={() => setNoteModalOpen(false)} style={{ padding: '4px' }}>
                <X size={16} />
              </button>
            </div>
            <form onSubmit={handleAddNoteSubmit}>
              <div className="modal-body">
                <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 600, marginBottom: '0.5rem' }}>
                  Underwriter Notes & Assessment Justification
                </label>
                <textarea
                  className="form-textarea"
                  rows={4}
                  placeholder="Enter notes regarding applicant verification, manual verification calls, or underwriting remarks..."
                  value={noteInput}
                  onChange={(e) => setNoteInput(e.target.value)}
                  required
                  style={{ width: '100%', fontSize: '0.85rem' }}
                />
              </div>
              <div className="modal-footer">
                <button type="button" className="btn btn-secondary" onClick={() => setNoteModalOpen(false)} disabled={submittingAction}>
                  Cancel
                </button>
                <button type="submit" className="btn btn-primary" disabled={submittingAction || !noteInput.trim()}>
                  {submittingAction ? 'Saving...' : 'Save Note to Audit Trail'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
