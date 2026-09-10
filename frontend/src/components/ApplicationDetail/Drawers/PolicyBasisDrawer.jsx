import React, { useState, useEffect } from 'react';
import { BookOpen, CheckCircle2, AlertCircle } from 'lucide-react';
import { api } from '../../../services/api';
import { formatPolicySourceLabel } from '../../../services/formatters';

export function PolicyBasisDrawer({ agentReview: initialAgentReview, applicationId }) {
  const [internalReview, setInternalReview] = useState(null);

  useEffect(() => {
    if (!initialAgentReview && applicationId) {
      api.getAgentReview(applicationId)
        .then((res) => setInternalReview(res))
        .catch(() => {});
    }
  }, [initialAgentReview, applicationId]);

  const agentReview = initialAgentReview || internalReview;
  const citations =
    agentReview?.final_review?.policy_references ||
    agentReview?.policy_references ||
    agentReview?.policy_citations ||
    [];

  return (
    <div className="policy-basis-drawer-wrap">
      <div style={{ marginBottom: '1.25rem' }}>
        <p
          style={{
            fontSize: '0.825rem',
            color: 'var(--color-text-secondary)',
            lineHeight: 1.45,
          }}
        >
          Statutory regulatory directives and internal underwriting rules cited
          by the review assessment.
        </p>
      </div>

      {citations.length === 0 ? (
        <div
          style={{
            padding: '2rem 1rem',
            textAlign: 'center',
            color: 'var(--color-text-muted)',
            fontSize: '0.825rem',
            background: 'var(--color-bg-subtle)',
            borderRadius: 'var(--radius-md)',
            border: '1px dashed var(--color-border)',
          }}
        >
          <BookOpen
            size={24}
            color="var(--color-text-muted)"
            style={{ margin: '0 auto 0.5rem' }}
          />
          <div>No specific policy citations referenced for this application.</div>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
          {citations.map((c, i) => {
            const label = formatPolicySourceLabel(c);
            const isRBI = label === 'RBI';
            const policyTitle =
              c.policy_name || c.title || c.section_title || c.policy_id || 'Underwriting Standard';
            const policyId = c.policy_id || null;
            const citationText =
              c.citation_text || c.content || c.snippet || c.rule_summary || '';

            return (
              <div
                key={i}
                style={{
                  padding: '1rem',
                  background: isRBI ? '#f0f9ff' : '#f8fafc',
                  border: isRBI ? '1px solid #bae6fd' : '1px solid var(--color-border)',
                  borderRadius: 'var(--radius-md)',
                  borderLeft: isRBI ? '4px solid #0284c7' : '4px solid #475569',
                }}
              >
                <div
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    marginBottom: '0.35rem',
                    gap: '0.5rem',
                  }}
                >
                  <span
                    className={`badge ${isRBI ? 'badge-info' : 'badge-neutral'}`}
                    style={{ fontSize: '0.7rem' }}
                  >
                    [{label}]
                  </span>
                  {policyId && (
                    <span
                      style={{
                        fontSize: '0.7rem',
                        color: 'var(--color-text-muted)',
                        fontFamily: 'var(--font-mono)',
                      }}
                    >
                      {policyId}
                    </span>
                  )}
                </div>
                <div
                  style={{
                    fontSize: '0.85rem',
                    fontWeight: 700,
                    color: 'var(--color-text-primary)',
                    marginBottom: '0.35rem',
                  }}
                >
                  {policyTitle}
                </div>
                {citationText && (
                  <p
                    style={{
                      fontSize: '0.775rem',
                      color: 'var(--color-text-secondary)',
                      lineHeight: 1.45,
                      margin: 0,
                    }}
                  >
                    {citationText}
                  </p>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
