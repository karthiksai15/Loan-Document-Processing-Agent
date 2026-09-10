import React, { useState } from 'react';
import {
  Sparkles,
  CheckCircle2,
  AlertTriangle,
  RefreshCw,
  FileText,
  BookOpen,
  ShieldCheck,
  HelpCircle,
  AlertCircle,
} from 'lucide-react';
import { api } from '../../../services/api';
import {
  formatPolicySourceLabel,
  formatAgentRecommendation,
} from '../../../services/formatters';

export function AIReviewDrawer({
  applicationId,
  agentReview,
  onReviewUpdated,
}) {
  const [running, setRunning] = useState(false);
  const [error, setError] = useState(null);

  const handleRunReview = async (force = true) => {
    try {
      setRunning(true);
      setError(null);
      const res = await api.runAgentReview(applicationId, force);
      if (onReviewUpdated) onReviewUpdated(res);
    } catch (err) {
      setError(err.message);
    } finally {
      setRunning(false);
    }
  };

  const hasReview = Boolean(
    agentReview && (agentReview.final_review || agentReview.investigation_status)
  );

  // If agent review is missing/null: show "Not Reviewed" and the Run AI Review CTA
  if (!hasReview) {
    return (
      <div className="ai-review-drawer-wrap">
        {/* Top Status */}
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            marginBottom: '1.25rem',
            paddingBottom: '0.75rem',
            borderBottom: '1px solid var(--color-border)',
          }}
        >
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '0.4rem',
              fontSize: '0.8rem',
              color: 'var(--color-text-muted)',
            }}
          >
            <Sparkles size={16} color="var(--color-primary-600)" />
            <span>AI Decision Support System</span>
          </div>
        </div>

        {error && (
          <div
            style={{
              marginBottom: '1rem',
              padding: '0.75rem',
              background: '#fef2f2',
              border: '1px solid #fecaca',
              borderRadius: 'var(--radius-md)',
              color: '#991b1b',
              fontSize: '0.825rem',
            }}
          >
            {error}
          </div>
        )}

        <div
          className="card"
          style={{
            padding: '2.5rem 1.25rem',
            textAlign: 'center',
            border: '1px dashed var(--color-border)',
            borderRadius: 'var(--radius-md)',
            marginBottom: '1.25rem',
          }}
        >
          <div style={{ marginBottom: '0.75rem' }}>
            <span
              className="badge badge-neutral"
              style={{ fontSize: '0.85rem', padding: '0.3rem 0.8rem' }}
            >
              Not Reviewed
            </span>
          </div>
          <h3
            style={{
              fontSize: '1.05rem',
              fontWeight: 700,
              color: 'var(--color-text-primary)',
              marginBottom: '0.5rem',
            }}
          >
            No AI Review Completed Yet
          </h3>
          <p
            style={{
              fontSize: '0.825rem',
              color: 'var(--color-text-secondary)',
              maxWidth: '380px',
              margin: '0 auto 1.5rem',
              lineHeight: 1.5,
            }}
          >
            Run the autonomous AI Review Agent to analyze applicant
            information, cross-document verification findings, and underwriting
            policies.
          </p>
          <button
            type="button"
            className="btn btn-primary"
            onClick={() => handleRunReview(false)}
            disabled={running}
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '0.5rem',
              margin: '0 auto',
            }}
          >
            <Sparkles size={15} className={running ? 'animate-spin' : ''} />
            <span>{running ? 'Investigating...' : 'Run AI Review'}</span>
          </button>
        </div>

        {/* Decision Support Boundary Notice */}
        <div
          style={{
            padding: '0.85rem 1rem',
            background: 'var(--color-bg-subtle)',
            border: '1px solid var(--color-border)',
            borderRadius: 'var(--radius-md)',
            display: 'flex',
            gap: '0.6rem',
            fontSize: '0.775rem',
            color: 'var(--color-text-muted)',
            lineHeight: 1.45,
          }}
        >
          <ShieldCheck
            size={18}
            color="var(--color-primary-600)"
            style={{ flexShrink: 0, marginTop: '2px' }}
          />
          <span>
            <strong>Decision Support Boundary:</strong> AI systems do not have
            authority to approve or reject credit applications. The final
            lending determination rests solely with the assigned credit
            underwriter.
          </span>
        </div>
      </div>
    );
  }

  // Extract all fields dynamically from agentReview and final_review
  const finalReview = agentReview.final_review || {};

  const investigationStatus = agentReview.investigation_status || 'COMPLETED';
  const rawRecommendation =
    finalReview.recommended_next_step ||
    agentReview.recommended_next_step ||
    agentReview.recommendation ||
    'STANDARD_REVIEW';
  const recLabel = formatAgentRecommendation(rawRecommendation);

  const rawConfidence = finalReview.confidence ?? agentReview.confidence;
  const confidence =
    rawConfidence !== undefined && rawConfidence !== null
      ? Math.round(rawConfidence <= 1 ? rawConfidence * 100 : rawConfidence)
      : null;

  const groundingStatus =
    finalReview.grounding_status || agentReview.grounding_status || 'GROUNDED';
  const isGrounded = groundingStatus === 'GROUNDED';
  const evidenceSufficiency =
    finalReview.evidence_sufficiency ||
    agentReview.evidence_sufficiency ||
    'SUFFICIENT';

  const executiveSummary =
    finalReview.executive_summary ||
    agentReview.executive_summary ||
    'No executive review summary provided.';

  const keyFindings =
    finalReview.key_findings || agentReview.key_findings || [];

  // Strictly dynamic evidence references from final_review.evidence_references
  const evidenceReferences =
    finalReview.evidence_references || agentReview.evidence_references || [];

  // Strictly dynamic policy references from final_review.policy_references
  const policyReferences =
    finalReview.policy_references ||
    agentReview.policy_references ||
    agentReview.policy_citations ||
    [];

  // Optional contextual sections where present
  const unresolvedQuestions =
    finalReview.unresolved_questions ||
    agentReview.unresolved_questions ||
    [];

  const limitations =
    finalReview.limitations || agentReview.limitations || [];

  // Badge styling for recommendation
  let recClass = 'badge-neutral';
  let borderLeftColor = '#3b82f6';
  const upperRec = String(rawRecommendation).toUpperCase();
  if (upperRec === 'STANDARD_REVIEW') {
    recClass = 'badge-low';
    borderLeftColor = '#22c55e';
  } else if (
    upperRec === 'OFFICER_INVESTIGATION' ||
    upperRec === 'DOCUMENT_FOLLOWUP'
  ) {
    recClass = 'badge-medium';
    borderLeftColor = '#f59e0b';
  } else if (upperRec === 'ESCALATE' || upperRec === 'ESCALATED') {
    recClass = 'badge-high';
    borderLeftColor = '#ef4444';
  }

  return (
    <div className="ai-review-drawer-wrap">
      {/* Top Status & Re-run action */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: '1.25rem',
          paddingBottom: '0.75rem',
          borderBottom: '1px solid var(--color-border)',
        }}
      >
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '0.5rem',
            fontSize: '0.8rem',
            color: 'var(--color-text-muted)',
          }}
        >
          <Sparkles size={16} color="var(--color-primary-600)" />
          <span>AI Decision Support System</span>
          <span
            className="badge badge-neutral"
            style={{ fontSize: '0.675rem', padding: '0.1rem 0.4rem' }}
          >
            {investigationStatus}
          </span>
        </div>
        <button
          type="button"
          className="btn btn-secondary btn-sm"
          onClick={() => handleRunReview(true)}
          disabled={running}
          style={{ display: 'inline-flex', alignItems: 'center', gap: '0.35rem' }}
        >
          <RefreshCw size={13} className={running ? 'animate-spin' : ''} />
          <span>{running ? 'Analyzing...' : 'Re-run AI Review'}</span>
        </button>
      </div>

      {error && (
        <div
          style={{
            marginBottom: '1rem',
            padding: '0.75rem',
            background: '#fef2f2',
            border: '1px solid #fecaca',
            borderRadius: 'var(--radius-md)',
            color: '#991b1b',
            fontSize: '0.825rem',
          }}
        >
          {error}
        </div>
      )}

      {/* Main Recommendation Card */}
      <div
        className="card"
        style={{
          padding: '1.25rem',
          marginBottom: '1.25rem',
          borderLeft: `4px solid ${borderLeftColor}`,
        }}
      >
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            marginBottom: '0.4rem',
          }}
        >
          <div
            style={{
              fontSize: '0.75rem',
              fontWeight: 600,
              color: 'var(--color-text-muted)',
              textTransform: 'uppercase',
              letterSpacing: '0.04em',
            }}
          >
            Recommendation
          </div>
          <span
            style={{
              fontSize: '0.7rem',
              color: 'var(--color-text-muted)',
              textTransform: 'uppercase',
              fontWeight: 600,
            }}
          >
            Status: {investigationStatus}
          </span>
        </div>

        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            flexWrap: 'wrap',
            gap: '0.5rem',
          }}
        >
          <span
            className={`badge ${recClass}`}
            style={{ fontSize: '0.9rem', padding: '0.35rem 0.85rem', fontWeight: 700 }}
          >
            {recLabel}
          </span>
          {confidence !== null && (
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <span style={{ fontSize: '0.8rem', color: 'var(--color-text-muted)' }}>
                Confidence:
              </span>
              <span
                style={{
                  fontSize: '1.1rem',
                  fontWeight: 700,
                  color: 'var(--color-text-primary)',
                }}
              >
                {confidence}%
              </span>
            </div>
          )}
        </div>

        {/* Verification & Grounding indicators */}
        <div
          style={{
            display: 'flex',
            gap: '1.25rem',
            marginTop: '0.85rem',
            paddingTop: '0.75rem',
            borderTop: '1px solid var(--color-border)',
            fontSize: '0.775rem',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
            <span style={{ color: 'var(--color-text-muted)' }}>Grounding:</span>
            <span
              style={{
                fontWeight: 600,
                color: isGrounded ? '#15803d' : '#b45309',
              }}
            >
              {groundingStatus}
            </span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
            <span style={{ color: 'var(--color-text-muted)' }}>Evidence:</span>
            <span
              style={{
                fontWeight: 600,
                color: evidenceSufficiency === 'SUFFICIENT' ? '#15803d' : '#b45309',
              }}
            >
              {evidenceSufficiency}
            </span>
          </div>
        </div>
      </div>

      {/* Summary Section */}
      <div style={{ marginBottom: '1.25rem' }}>
        <h4
          style={{
            fontSize: '0.85rem',
            fontWeight: 700,
            textTransform: 'uppercase',
            letterSpacing: '0.04em',
            color: 'var(--color-text-muted)',
            marginBottom: '0.5rem',
          }}
        >
          Executive Summary
        </h4>
        <div
          style={{
            fontSize: '0.875rem',
            color: 'var(--color-text-primary)',
            lineHeight: 1.55,
            background: '#f8fafc',
            padding: '0.85rem 1rem',
            borderRadius: 'var(--radius-md)',
            border: '1px solid var(--color-border)',
          }}
        >
          {executiveSummary}
        </div>
      </div>

      {/* Key Findings */}
      {keyFindings.length > 0 && (
        <div style={{ marginBottom: '1.25rem' }}>
          <h4
            style={{
              fontSize: '0.85rem',
              fontWeight: 700,
              textTransform: 'uppercase',
              letterSpacing: '0.04em',
              color: 'var(--color-text-muted)',
              marginBottom: '0.5rem',
            }}
          >
            Key Findings ({keyFindings.length})
          </h4>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.4rem' }}>
            {keyFindings.map((finding, idx) => (
              <div
                key={idx}
                style={{
                  display: 'flex',
                  alignItems: 'flex-start',
                  gap: '0.5rem',
                  fontSize: '0.825rem',
                  color: 'var(--color-text-secondary)',
                  padding: '0.5rem 0.75rem',
                  background: '#ffffff',
                  border: '1px solid var(--color-border)',
                  borderRadius: 'var(--radius-md)',
                }}
              >
                <AlertTriangle
                  size={15}
                  color="#d97706"
                  style={{ flexShrink: 0, marginTop: '2px' }}
                />
                <span>{finding}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Evidence Examined (derived directly from final_review.evidence_references) */}
      <div style={{ marginBottom: '1.25rem' }}>
        <h4
          style={{
            fontSize: '0.85rem',
            fontWeight: 700,
            textTransform: 'uppercase',
            letterSpacing: '0.04em',
            color: 'var(--color-text-muted)',
            marginBottom: '0.5rem',
          }}
        >
          Evidence Examined ({evidenceReferences.length})
        </h4>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.4rem' }}>
          {evidenceReferences.length > 0 ? (
            evidenceReferences.map((ev, i) => {
              const isObj = typeof ev === 'object' && ev !== null;
              const desc = isObj
                ? ev.description || ev.name || ev.reference || ev.node_id || 'Evidence Node'
                : String(ev);
              const nodeId = isObj ? ev.node_id : null;

              return (
                <div
                  key={i}
                  style={{
                    display: 'flex',
                    alignItems: 'flex-start',
                    gap: '0.5rem',
                    fontSize: '0.8rem',
                    color: 'var(--color-text-primary)',
                    padding: '0.45rem 0.65rem',
                    background: '#f8fafc',
                    border: '1px solid var(--color-border)',
                    borderRadius: 'var(--radius-sm)',
                  }}
                >
                  <CheckCircle2
                    size={15}
                    color="#16a34a"
                    style={{ flexShrink: 0, marginTop: '2px' }}
                  />
                  <div style={{ flex: 1, lineHeight: 1.45 }}>
                    {nodeId && (
                      <span
                        className="badge badge-neutral"
                        style={{
                          fontSize: '0.65rem',
                          marginRight: '0.4rem',
                          padding: '0.08rem 0.35rem',
                          fontFamily: 'var(--font-mono)',
                        }}
                      >
                        {nodeId}
                      </span>
                    )}
                    <span>{desc}</span>
                  </div>
                </div>
              );
            })
          ) : (
            <div
              style={{
                fontSize: '0.8rem',
                color: 'var(--color-text-muted)',
                padding: '0.5rem',
              }}
            >
              No specific evidence references recorded.
            </div>
          )}
        </div>
      </div>

      {/* Policy Basis (derived directly from final_review.policy_references) */}
      <div style={{ marginBottom: '1.25rem' }}>
        <h4
          style={{
            fontSize: '0.85rem',
            fontWeight: 700,
            textTransform: 'uppercase',
            letterSpacing: '0.04em',
            color: 'var(--color-text-muted)',
            marginBottom: '0.5rem',
          }}
        >
          Policy Basis ({policyReferences.length})
        </h4>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
          {policyReferences.length > 0 ? (
            policyReferences.map((pol, i) => {
              const label = formatPolicySourceLabel(pol);
              const isRBI = label === 'RBI';
              const policyId = pol.policy_id || null;
              const policyTitle =
                pol.policy_name || pol.title || pol.section_title || policyId || 'Policy Standard';
              const citationText =
                pol.citation_text || pol.content || pol.snippet || pol.rule_summary || null;

              return (
                <div
                  key={i}
                  style={{
                    padding: '0.75rem 0.85rem',
                    background: isRBI ? '#f0f9ff' : '#f8fafc',
                    border: isRBI ? '1px solid #bae6fd' : '1px solid var(--color-border)',
                    borderRadius: 'var(--radius-md)',
                    borderLeft: isRBI ? '4px solid #0284c7' : '4px solid #475569',
                    fontSize: '0.8rem',
                  }}
                >
                  <div
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      marginBottom: '0.25rem',
                      gap: '0.5rem',
                    }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                      <span
                        className={`badge ${isRBI ? 'badge-info' : 'badge-neutral'}`}
                        style={{ fontSize: '0.675rem' }}
                      >
                        [{label}]
                      </span>
                      <span
                        style={{
                          fontWeight: 700,
                          color: 'var(--color-text-primary)',
                        }}
                      >
                        {policyTitle}
                      </span>
                    </div>
                    {policyId && (
                      <span
                        style={{
                          fontSize: '0.675rem',
                          color: 'var(--color-text-muted)',
                          fontFamily: 'var(--font-mono)',
                        }}
                      >
                        {policyId}
                      </span>
                    )}
                  </div>
                  {citationText && (
                    <p
                      style={{
                        fontSize: '0.75rem',
                        color: 'var(--color-text-secondary)',
                        margin: '0.25rem 0 0 0',
                        lineHeight: 1.45,
                      }}
                    >
                      {citationText}
                    </p>
                  )}
                </div>
              );
            })
          ) : (
            <div
              style={{
                fontSize: '0.8rem',
                color: 'var(--color-text-muted)',
                padding: '0.5rem',
              }}
            >
              No specific policy references cited for this review.
            </div>
          )}
        </div>
      </div>

      {/* Unresolved Questions (where present) */}
      {unresolvedQuestions.length > 0 && (
        <div style={{ marginBottom: '1.25rem' }}>
          <h4
            style={{
              fontSize: '0.85rem',
              fontWeight: 700,
              textTransform: 'uppercase',
              letterSpacing: '0.04em',
              color: 'var(--color-text-muted)',
              marginBottom: '0.5rem',
            }}
          >
            Unresolved Questions ({unresolvedQuestions.length})
          </h4>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.4rem' }}>
            {unresolvedQuestions.map((q, idx) => (
              <div
                key={idx}
                style={{
                  display: 'flex',
                  alignItems: 'flex-start',
                  gap: '0.5rem',
                  fontSize: '0.825rem',
                  color: '#854d0e',
                  padding: '0.5rem 0.75rem',
                  background: '#fefce8',
                  border: '1px solid #fef08a',
                  borderRadius: 'var(--radius-md)',
                }}
              >
                <HelpCircle
                  size={15}
                  color="#ca8a04"
                  style={{ flexShrink: 0, marginTop: '2px' }}
                />
                <span>{q}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Limitations (where present) */}
      {limitations.length > 0 && (
        <div style={{ marginBottom: '1.25rem' }}>
          <h4
            style={{
              fontSize: '0.85rem',
              fontWeight: 700,
              textTransform: 'uppercase',
              letterSpacing: '0.04em',
              color: 'var(--color-text-muted)',
              marginBottom: '0.5rem',
            }}
          >
            Analysis Limitations ({limitations.length})
          </h4>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.4rem' }}>
            {limitations.map((lim, idx) => (
              <div
                key={idx}
                style={{
                  display: 'flex',
                  alignItems: 'flex-start',
                  gap: '0.5rem',
                  fontSize: '0.825rem',
                  color: 'var(--color-text-secondary)',
                  padding: '0.5rem 0.75rem',
                  background: '#f8fafc',
                  border: '1px solid var(--color-border)',
                  borderRadius: 'var(--radius-md)',
                }}
              >
                <AlertCircle
                  size={15}
                  color="#64748b"
                  style={{ flexShrink: 0, marginTop: '2px' }}
                />
                <span>{lim}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Decision Support Boundary Notice */}
      <div
        style={{
          padding: '0.85rem 1rem',
          background: 'var(--color-bg-subtle)',
          border: '1px solid var(--color-border)',
          borderRadius: 'var(--radius-md)',
          display: 'flex',
          gap: '0.6rem',
          fontSize: '0.775rem',
          color: 'var(--color-text-muted)',
          lineHeight: 1.45,
        }}
      >
        <ShieldCheck
          size={18}
          color="var(--color-primary-600)"
          style={{ flexShrink: 0, marginTop: '2px' }}
        />
        <span>
          <strong>Decision Support Boundary:</strong> AI systems do not have
          authority to approve or reject credit applications. The final
          lending determination rests solely with the assigned credit
          underwriter.
        </span>
      </div>
    </div>
  );
}
