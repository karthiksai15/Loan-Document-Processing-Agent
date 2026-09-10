import React, { useEffect, useState } from 'react';
import { History, Award, CheckCircle2, AlertTriangle, MessageSquare, Clock } from 'lucide-react';
import { api } from '../../services/api';
import { StatusBadge } from '../Common/Badges';
import { formatDateTime } from '../../services/formatters';
import { LoadingState } from '../Common/LoadingState';
import { ErrorAlert } from '../Common/ErrorAlert';

export function DecisionHistoryTab({ applicationId }) {
  const [historyData, setHistoryData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let isMounted = true;
    async function fetchHistory() {
      try {
        setLoading(true);
        setError(null);
        const res = await api.getDecisionHistory(applicationId);
        if (isMounted) setHistoryData(res);
      } catch (err) {
        if (isMounted) setError(err.message);
      } finally {
        if (isMounted) setLoading(false);
      }
    }

    fetchHistory();
    return () => {
      isMounted = false;
    };
  }, [applicationId]);

  if (loading) return <LoadingState message="Loading decision timeline & audit history..." />;
  if (error) return <ErrorAlert message={error} />;
  if (!historyData) return null;

  const auditEvents = historyData.audit_trail || [];
  const feedbackList = historyData.feedback || [];
  const alignment = historyData.alignment_status || 'PENDING';

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
      {/* Comparison Header Card */}
      <div className="card" style={{ padding: '1.25rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '1rem', marginBottom: '1rem' }}>
          <div>
            <h4 style={{ fontSize: '1rem', fontWeight: 600 }}>
              AI Recommendation vs Human Decision Alignment
            </h4>
            <span style={{ fontSize: '0.775rem', color: 'var(--color-text-muted)' }}>
              Independent decision boundary analysis
            </span>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <span style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--color-text-muted)', textTransform: 'uppercase' }}>
              Alignment Status:
            </span>
            <span className={`badge ${alignment === 'ALIGNED' ? 'badge-low' : alignment === 'OVERRIDDEN' ? 'badge-medium' : 'badge-neutral'}`}>
              <span className="badge-dot" />
              <span>{alignment}</span>
            </span>
          </div>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '1rem' }}>
          <div style={{ background: 'var(--color-bg-subtle)', padding: '1rem', borderRadius: 'var(--radius-md)', border: '1px solid var(--color-border)' }}>
            <div style={{ fontSize: '0.725rem', fontWeight: 600, color: 'var(--color-text-muted)', textTransform: 'uppercase', marginBottom: '0.25rem' }}>
              AI Recommendation
            </div>
            <div style={{ fontSize: '1.15rem', fontWeight: 700, color: 'var(--color-primary-700)' }}>
              {historyData.ai_recommendation ? historyData.ai_recommendation.replace(/_/g, ' ') : 'PENDING'}
            </div>
            <div style={{ fontSize: '0.75rem', color: 'var(--color-text-muted)', marginTop: '0.25rem' }}>
              Operational guidance produced by AI review agent
            </div>
          </div>

          <div style={{ background: 'var(--color-bg-subtle)', padding: '1rem', borderRadius: 'var(--radius-md)', border: `1px solid ${historyData.human_decision === 'APPROVED' ? 'var(--color-success-border)' : historyData.human_decision === 'REJECTED' ? 'var(--color-danger-border)' : 'var(--color-border)'}` }}>
            <div style={{ fontSize: '0.725rem', fontWeight: 600, color: 'var(--color-text-muted)', textTransform: 'uppercase', marginBottom: '0.25rem' }}>
              Final Human Decision
            </div>
            <div style={{ fontSize: '1.15rem', fontWeight: 700, color: historyData.human_decision === 'APPROVED' ? '#15803d' : historyData.human_decision === 'REJECTED' ? '#b91c1c' : 'var(--color-text-primary)' }}>
              {historyData.human_decision || 'AWAITING DECISION'}
            </div>
            {historyData.decision_reason && (
              <div style={{ fontSize: '0.8rem', color: 'var(--color-text-secondary)', marginTop: '0.25rem' }}>
                <strong>Reason:</strong> {historyData.decision_reason}
              </div>
            )}
            {historyData.override_reason && (
              <div style={{ fontSize: '0.775rem', color: 'var(--color-warning-text)', marginTop: '0.2rem' }}>
                <strong>Override:</strong> {historyData.override_reason}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Chronological Audit Timeline */}
      <div className="card">
        <div className="card-header">
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <History size={16} color="var(--color-primary-600)" />
            <h4 style={{ fontSize: '0.9rem', fontWeight: 600 }}>Decision Audit Timeline</h4>
          </div>
          <span style={{ fontSize: '0.75rem', color: 'var(--color-text-muted)' }}>
            {auditEvents.length} Immutable Events
          </span>
        </div>

        <div className="card-body">
          {auditEvents.length > 0 ? (
            <div className="timeline">
              {auditEvents.map((ev, i) => (
                <div key={i} className="timeline-item">
                  <div className="timeline-dot" />
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.2rem' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                      <strong style={{ fontSize: '0.85rem', color: 'var(--color-text-primary)' }}>
                        {ev.action.replace(/_/g, ' ')}
                      </strong>
                      <span className="badge badge-neutral" style={{ fontSize: '0.65rem' }}>
                        {ev.actor_type || 'SYSTEM'}
                      </span>
                    </div>
                    <span style={{ fontSize: '0.75rem', color: 'var(--color-text-muted)', display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
                      <Clock size={12} />
                      {formatDateTime(ev.timestamp)}
                    </span>
                  </div>

                  <p style={{ fontSize: '0.825rem', color: 'var(--color-text-secondary)' }}>
                    {ev.note}
                  </p>

                  {(ev.previous_status || ev.new_status) && (
                    <div style={{ fontSize: '0.75rem', color: 'var(--color-text-muted)', marginTop: '0.2rem' }}>
                      Status transition: <code>{ev.previous_status || 'NONE'}</code> ➔ <code>{ev.new_status || 'CURRENT'}</code>
                    </div>
                  )}
                </div>
              ))}
            </div>
          ) : (
            <div style={{ fontSize: '0.825rem', color: 'var(--color-text-muted)', fontStyle: 'italic' }}>
              No audit timeline events recorded yet.
            </div>
          )}
        </div>
      </div>

      {/* Officer Feedback Records */}
      {feedbackList.length > 0 && (
        <div className="card">
          <div className="card-header">
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <MessageSquare size={16} color="var(--color-primary-600)" />
              <h4 style={{ fontSize: '0.9rem', fontWeight: 600 }}>
                Officer Qualitative Feedback ({feedbackList.length})
              </h4>
            </div>
          </div>

          <div className="card-body" style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
            {feedbackList.map((fb, idx) => (
              <div key={idx} style={{ padding: '0.875rem', background: 'var(--color-bg-subtle)', borderRadius: 'var(--radius-md)', border: '1px solid var(--color-border)' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.35rem' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <strong style={{ fontSize: '0.825rem' }}>{fb.officer_id}</strong>
                    <span className={`badge ${fb.category === 'CORRECT' ? 'badge-low' : fb.category === 'INCORRECT' ? 'badge-high' : 'badge-medium'}`} style={{ fontSize: '0.675rem' }}>
                      {fb.category || 'FEEDBACK'}
                    </span>
                  </div>
                  <span style={{ fontSize: '0.75rem', color: 'var(--color-text-muted)' }}>
                    {formatDateTime(fb.timestamp)}
                  </span>
                </div>
                <p style={{ fontSize: '0.825rem', color: 'var(--color-text-primary)' }}>
                  "{fb.feedback}"
                </p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
