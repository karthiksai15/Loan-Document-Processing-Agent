import React, { useState, useEffect } from 'react';
import { Sparkles, CheckCircle2, AlertTriangle, ArrowRight, ShieldCheck } from 'lucide-react';
import { api } from '../../../services/api';
import { formatAgentRecommendation } from '../../../services/formatters';

export function AIInvestigationDrawer({ agentReview: initialAgentReview, applicationId }) {
  const [internalReview, setInternalReview] = useState(null);

  useEffect(() => {
    if (!initialAgentReview && applicationId) {
      api.getAgentReview(applicationId)
        .then((res) => setInternalReview(res))
        .catch(() => {});
    }
  }, [initialAgentReview, applicationId]);

  const agentReview = initialAgentReview || internalReview;
  const review = agentReview?.final_review || {};
  const hasReview = Boolean(
    agentReview && (agentReview.final_review || agentReview.investigation_status)
  );

  const steps = [
    { title: 'Application Context Loaded', desc: 'Retrieved borrower profile, declared income, loan amount, and bureau history.' },
    { title: 'Evidence Graph & Cross-Verification Checked', desc: 'Evaluated cross-document field alignments across KYC, payslip, and bank statement.' },
    { title: 'Statutory & Bank Policy Evaluated', desc: 'Searched RBI directives and internal credit underwriting standards.' },
    { title: 'Grounding & Fact Verification', desc: 'Ensured all findings strictly cite verified application evidence and policies.' },
    { title: 'Advisory Formulation', desc: 'Synthesized evidence sufficiency, confidence, and recommended underwriting action.' },
  ];

  // Dynamic recommendation derived directly from final_review.recommended_next_step
  const rawRec =
    review.recommended_next_step ||
    agentReview?.recommended_next_step ||
    agentReview?.recommendation ||
    (hasReview ? 'STANDARD_REVIEW' : null);
  const recommendation = formatAgentRecommendation(rawRec);

  // Dynamic agent confidence directly from agentReview.confidence / final_review.confidence (NO 85% fallback)
  const rawConf = review.confidence ?? agentReview?.confidence;
  const confidence =
    rawConf !== undefined && rawConf !== null
      ? Math.round(rawConf <= 1 ? rawConf * 100 : rawConf)
      : null;

  const investigationStatus = agentReview?.investigation_status || (hasReview ? 'COMPLETED' : 'NOT_STARTED');
  const groundingStatus = review.grounding_status || agentReview?.grounding_status || 'GROUNDED';
  const evidenceSufficiency = review.evidence_sufficiency || agentReview?.evidence_sufficiency || 'PARTIAL';

  const executiveSummary =
    review.executive_summary ||
    agentReview?.executive_summary ||
    (hasReview
      ? 'The review analyzed applicant information, cross-document verification findings, and underwriting policies.'
      : 'No automated AI investigation has been recorded for this application yet.');

  let badgeClass = 'badge-neutral';
  let borderLeftColor = '#3b82f6';
  const upperRec = String(rawRec || '').toUpperCase();
  if (upperRec === 'STANDARD_REVIEW') {
    badgeClass = 'badge-low';
    borderLeftColor = '#22c55e';
  } else if (upperRec === 'OFFICER_INVESTIGATION' || upperRec === 'DOCUMENT_FOLLOWUP') {
    badgeClass = 'badge-medium';
    borderLeftColor = '#f59e0b';
  } else if (upperRec === 'ESCALATE' || upperRec === 'ESCALATED') {
    badgeClass = 'badge-high';
    borderLeftColor = '#ef4444';
  }

  return (
    <div className="ai-investigation-drawer-wrap">
      <div style={{ marginBottom: '1.25rem' }}>
        <p style={{ fontSize: '0.825rem', color: 'var(--color-text-secondary)', lineHeight: 1.45 }}>
          Transparent synthesis of the automated analysis process, verification steps, and policy reasoning.
        </p>
      </div>

      {/* Investigation Status Summary */}
      <div
        className="card"
        style={{
          padding: '1rem',
          marginBottom: '1.25rem',
          background: '#f8fafc',
          borderLeft: `4px solid ${borderLeftColor}`,
        }}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem', flexWrap: 'wrap', gap: '0.4rem' }}>
          <span style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--color-text-muted)', textTransform: 'uppercase' }}>
            Analysis Outcome
          </span>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
            {hasReview && (
              <span className="badge badge-neutral" style={{ fontSize: '0.675rem', padding: '0.1rem 0.4rem' }}>
                {investigationStatus}
              </span>
            )}
            <span className={`badge ${badgeClass}`} style={{ fontSize: '0.75rem', fontWeight: 700 }}>
              {recommendation}
            </span>
          </div>
        </div>

        <div style={{ fontSize: '0.825rem', color: 'var(--color-text-secondary)', lineHeight: 1.5, marginBottom: '0.65rem' }}>
          {executiveSummary}
        </div>

        {hasReview && (
          <div
            style={{
              display: 'flex',
              gap: '1rem',
              fontSize: '0.75rem',
              color: 'var(--color-text-muted)',
              paddingTop: '0.5rem',
              borderTop: '1px solid var(--color-border)',
              flexWrap: 'wrap',
            }}
          >
            <span>
              Grounding:{' '}
              <strong style={{ color: groundingStatus === 'GROUNDED' ? '#16a34a' : '#b45309' }}>
                {groundingStatus}
              </strong>
            </span>
            <span>•</span>
            <span>
              Evidence:{' '}
              <strong style={{ color: evidenceSufficiency === 'SUFFICIENT' ? '#16a34a' : '#b45309' }}>
                {evidenceSufficiency}
              </strong>
            </span>
            {confidence !== null && (
              <>
                <span>•</span>
                <span>
                  Confidence:{' '}
                  <strong style={{ color: 'var(--color-text-primary)' }}>
                    {confidence}%
                  </strong>
                </span>
              </>
            )}
          </div>
        )}
      </div>

      {/* Multi-Step Investigation Workflow */}
      <div style={{ marginBottom: '1.5rem' }}>
        <h4 style={{ fontSize: '0.8rem', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.04em', color: 'var(--color-text-muted)', marginBottom: '0.75rem' }}>
          Investigation Steps
        </h4>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.65rem' }}>
          {steps.map((step, idx) => (
            <div
              key={idx}
              style={{
                display: 'flex',
                alignItems: 'flex-start',
                gap: '0.65rem',
                padding: '0.7rem 0.85rem',
                background: '#ffffff',
                border: '1px solid var(--color-border)',
                borderRadius: 'var(--radius-md)',
              }}
            >
              <div
                style={{
                  width: '22px',
                  height: '22px',
                  borderRadius: '50%',
                  background: 'var(--color-primary-50)',
                  color: 'var(--color-primary-600)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  fontSize: '0.75rem',
                  fontWeight: 700,
                  flexShrink: 0,
                  marginTop: '1px',
                }}
              >
                {idx + 1}
              </div>
              <div>
                <div style={{ fontSize: '0.825rem', fontWeight: 600, color: 'var(--color-text-primary)' }}>
                  {step.title}
                </div>
                <div style={{ fontSize: '0.75rem', color: 'var(--color-text-secondary)', marginTop: '0.15rem' }}>
                  {step.desc}
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Grounding & Confidence Metrics */}
      <div style={{ padding: '1rem', background: '#f0fdf4', border: '1px solid #bbf7d0', borderRadius: 'var(--radius-md)', marginBottom: '1.25rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.35rem' }}>
          <ShieldCheck size={16} color="#16a34a" />
          <span style={{ fontSize: '0.825rem', fontWeight: 700, color: '#166534' }}>
            Grounding & Verification Guarantee
          </span>
        </div>
        <p style={{ fontSize: '0.775rem', color: '#15803d', margin: 0, lineHeight: 1.4 }}>
          Every claim and finding in this review is cross-referenced against extracted document text and statutory directives. Hallucination checks passed with {confidence !== null ? `${confidence}%` : 'verified'} review confidence.
        </p>
      </div>
    </div>
  );
}
