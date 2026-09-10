import React, { useState } from 'react';
import {
  Bot,
  ShieldCheck,
  FileCheck2,
  AlertTriangle,
  Play,
  RotateCw,
  HelpCircle,
  ExternalLink,
} from 'lucide-react';
import { api } from '../../services/api';
import { StatusBadge, ConfidenceBadge } from '../Common/Badges';
import { LoadingState } from '../Common/LoadingState';
import { ErrorAlert } from '../Common/ErrorAlert';

export function AIReviewTab({ applicationId, agentReview, onRefresh }) {
  const [running, setRunning] = useState(false);
  const [error, setError] = useState(null);

  const handleRunReview = async (force = true) => {
    try {
      setRunning(true);
      setError(null);
      await api.runAgentReview(applicationId, force);
      if (onRefresh) onRefresh();
    } catch (err) {
      setError(err.message);
    } finally {
      setRunning(false);
    }
  };

  if (!agentReview) {
    return (
      <div className="card" style={{ padding: '2.5rem 1.5rem', textAlign: 'center' }}>
        <Bot size={40} color="var(--color-primary-600)" style={{ margin: '0 auto 1rem' }} />
        <h3 style={{ fontSize: '1.1rem', fontWeight: 600, color: 'var(--color-text-primary)', marginBottom: '0.5rem' }}>
          No AI Agent Investigation Run Yet
        </h3>
        <p style={{ fontSize: '0.85rem', color: 'var(--color-text-secondary)', maxWidth: '480px', margin: '0 auto 1.5rem' }}>
          Launch the Decision Support AI Loan Review Agent. The agent iteratively investigates the application, cross-checks evidence against bank and regulatory policies, and compiles an explainable report for officer review.
        </p>
        {error && <ErrorAlert message={error} />}
        {running ? (
          <LoadingState message="Running AI investigation workflow..." />
        ) : (
          <button
            type="button"
            className="btn btn-primary"
            onClick={() => handleRunReview(true)}
            style={{ display: 'inline-flex', alignItems: 'center', gap: '0.5rem' }}
          >
            <Play size={16} />
            <span>Launch AI Agent Investigation</span>
          </button>
        )}
      </div>
    );
  }

  const review = agentReview.final_review || {};
  const steps = agentReview.investigation_steps || [];
  const recommendation = review.recommended_next_step || 'OFFICER_INVESTIGATION';

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
      {/* AI Recommendation Banner */}
      <div
        className="card"
        style={{
          borderLeft: '5px solid var(--color-primary-600)',
          background: 'linear-gradient(to right, #f0f9ff, #ffffff)',
          padding: '1.25rem 1.5rem',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', flexWrap: 'wrap', gap: '1rem' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.35rem' }}>
              <Bot size={18} color="var(--color-primary-600)" />
              <span style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--color-primary-700)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                AI Review Agent Recommendation
              </span>
            </div>
            <div style={{ fontSize: '1.5rem', fontWeight: 700, color: 'var(--color-text-primary)', marginBottom: '0.25rem' }}>
              {recommendation.replace(/_/g, ' ')}
            </div>
            <p style={{ fontSize: '0.8rem', color: 'var(--color-text-muted)' }}>
              Operational guidance only. <strong>The final credit decision belongs to the human loan officer.</strong>
            </p>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', flexWrap: 'wrap' }}>
            <div style={{ textAlign: 'right' }}>
              <div style={{ fontSize: '0.7rem', color: 'var(--color-text-muted)', textTransform: 'uppercase', fontWeight: 600 }}>
                AI Confidence
              </div>
              <ConfidenceBadge level={review.confidence_level || agentReview.confidence_level} score={review.confidence ?? agentReview.confidence} />
            </div>

            <div style={{ textAlign: 'right' }}>
              <div style={{ fontSize: '0.7rem', color: 'var(--color-text-muted)', textTransform: 'uppercase', fontWeight: 600 }}>
                Grounding Status
              </div>
              <StatusBadge status={agentReview.grounding_status || 'GROUNDED'} />
            </div>

            <button
              type="button"
              className="btn btn-secondary btn-sm"
              onClick={() => handleRunReview(true)}
              disabled={running}
              style={{ marginLeft: '0.5rem' }}
            >
              <RotateCw size={14} className={running ? 'animate-spin' : ''} />
              <span>{running ? 'Investigating...' : 'Re-run Agent'}</span>
            </button>
          </div>
        </div>
      </div>

      {error && <ErrorAlert message={error} />}

      {/* Executive Narrative */}
      <div className="card">
        <div className="card-header">
          <h3 style={{ fontSize: '0.95rem', fontWeight: 600 }}>Executive Summary</h3>
          <span style={{ fontSize: '0.75rem', color: 'var(--color-text-muted)' }}>
            Investigation Steps: {agentReview.step_count || steps.length} • Tools: {agentReview.tools_used?.join(', ') || 'Standard Suite'}
          </span>
        </div>
        <div className="card-body">
          <p style={{ fontSize: '0.925rem', lineHeight: 1.6, color: 'var(--color-text-primary)' }}>
            {review.executive_summary || 'No executive summary provided by agent.'}
          </p>

          {/* Key Findings */}
          {review.key_findings && review.key_findings.length > 0 && (
            <div style={{ marginTop: '1.25rem' }}>
              <h4 style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--color-text-secondary)', marginBottom: '0.5rem', textTransform: 'uppercase' }}>
                Key Findings
              </h4>
              <ul style={{ paddingLeft: '1.25rem', fontSize: '0.875rem', lineHeight: 1.5, color: 'var(--color-text-primary)' }}>
                {review.key_findings.map((f, i) => (
                  <li key={i} style={{ marginBottom: '0.35rem' }}>
                    {f}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      </div>

      {/* Grounded Evidence & Policy Citations Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '1rem' }}>
        {/* Evidence Citations */}
        <div className="card">
          <div className="card-header">
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <FileCheck2 size={16} color="var(--color-primary-600)" />
              <h4 style={{ fontSize: '0.9rem', fontWeight: 600 }}>Evidence Graph Citations</h4>
            </div>
            <span style={{ fontSize: '0.75rem', color: 'var(--color-text-muted)' }}>
              {review.evidence_references?.length || 0} Grounded Nodes
            </span>
          </div>
          <div className="card-body" style={{ maxHeight: '280px', overflowY: 'auto' }}>
            {review.evidence_references && review.evidence_references.length > 0 ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                {review.evidence_references.map((ref, i) => (
                  <div key={i} style={{ padding: '0.625rem', background: 'var(--color-bg-subtle)', borderRadius: 'var(--radius-md)', border: '1px solid var(--color-border)', fontSize: '0.825rem' }}>
                    <div style={{ fontFamily: 'var(--font-mono)', fontSize: '0.75rem', color: 'var(--color-primary-700)', fontWeight: 600, marginBottom: '0.2rem' }}>
                      {ref.node_id}
                    </div>
                    <div style={{ color: 'var(--color-text-secondary)' }}>
                      {ref.description}
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div style={{ fontSize: '0.825rem', color: 'var(--color-text-muted)', fontStyle: 'italic' }}>
                No explicit evidence citations recorded.
              </div>
            )}
          </div>
        </div>

        {/* Policy Citations */}
        <div className="card">
          <div className="card-header">
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <ShieldCheck size={16} color="var(--color-primary-600)" />
              <h4 style={{ fontSize: '0.9rem', fontWeight: 600 }}>Policy Citations (Policy Knowledge Base)</h4>
            </div>
            <span style={{ fontSize: '0.75rem', color: 'var(--color-text-muted)' }}>
              {review.policy_references?.length || 0} Retrieved Sections
            </span>
          </div>
          <div className="card-body" style={{ maxHeight: '280px', overflowY: 'auto' }}>
            {review.policy_references && review.policy_references.length > 0 ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                {review.policy_references.map((p, i) => (
                  <div key={i} style={{ padding: '0.625rem', background: 'var(--color-bg-subtle)', borderRadius: 'var(--radius-md)', border: '1px solid var(--color-border)', fontSize: '0.825rem' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.25rem' }}>
                      <span className={`badge ${p.authority === 'RBI' ? 'badge-info' : 'badge-neutral'}`} style={{ fontSize: '0.65rem' }}>
                        {p.authority === 'RBI' ? '🏛 RBI REGULATORY' : '🏢 INTERNAL BANK'}
                      </span>
                      <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.7rem', color: 'var(--color-text-muted)' }}>
                        {p.section_id}
                      </span>
                    </div>
                    <div style={{ fontWeight: 600, color: 'var(--color-text-primary)', marginBottom: '0.2rem' }}>
                      {p.policy_name}
                    </div>
                    <div style={{ color: 'var(--color-text-secondary)', fontSize: '0.8rem', lineHeight: 1.4 }}>
                      "{p.citation_text}"
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div style={{ fontSize: '0.825rem', color: 'var(--color-text-muted)', fontStyle: 'italic' }}>
                No explicit policy citations recorded.
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Investigation Trace Timeline */}
      {steps.length > 0 && (
        <div className="card">
          <div className="card-header">
            <h4 style={{ fontSize: '0.9rem', fontWeight: 600 }}>Agent Investigation Trace</h4>
            <span style={{ fontSize: '0.75rem', color: 'var(--color-text-muted)' }}>
              Investigation steps & evidence verification sequence
            </span>
          </div>
          <div className="card-body">
            <div className="timeline">
              {steps.map((step, idx) => (
                <div key={idx} className="timeline-item">
                  <div className="timeline-dot" />
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.25rem' }}>
                    <span style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--color-primary-700)', textTransform: 'uppercase' }}>
                      Step {step.step_number || idx + 1}: {step.action}
                    </span>
                    {step.tool_name && (
                      <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.725rem', background: 'var(--color-primary-50)', color: 'var(--color-primary-700)', padding: '0.1rem 0.4rem', borderRadius: 'var(--radius-sm)' }}>
                        action: {step.tool_name}
                      </span>
                    )}
                  </div>
                  <p style={{ fontSize: '0.825rem', color: 'var(--color-text-secondary)', marginBottom: '0.25rem' }}>
                    <strong>Finding:</strong> {step.result_summary}
                  </p>
                  {step.reason && (
                    <div style={{ fontSize: '0.775rem', color: 'var(--color-text-muted)', fontStyle: 'italic' }}>
                      Reason: {step.reason}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
