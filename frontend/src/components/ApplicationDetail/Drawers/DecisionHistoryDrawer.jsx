import React, { useEffect, useState } from 'react';
import { History, CheckCircle2, AlertTriangle, MessageSquare, Clock, User, ShieldCheck } from 'lucide-react';
import { api } from '../../../services/api';
import { formatDateTime } from '../../../services/formatters';

export function DecisionHistoryDrawer({ applicationId }) {
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

  if (loading) {
    return <div style={{ padding: '2rem', textAlign: 'center', color: 'var(--color-text-muted)' }}>Loading decision history...</div>;
  }

  if (error) {
    return <div style={{ padding: '1rem', color: '#991b1b', background: '#fef2f2', borderRadius: 'var(--radius-md)' }}>{error}</div>;
  }

  const auditEvents = historyData?.audit_trail || [];
  const feedbackList = historyData?.feedback || [];
  const alignment = historyData?.alignment_status || 'PENDING';
  const isOverridden = alignment === 'OVERRIDDEN';

  return (
    <div className="decision-history-drawer-wrap">
      <div style={{ marginBottom: '1.25rem' }}>
        <p style={{ fontSize: '0.825rem', color: 'var(--color-text-secondary)', lineHeight: 1.45 }}>
          Immutable audit records of all automated analysis, loan officer acknowledgements, notes, and final credit decisions.
        </p>
      </div>

      {/* Alignment Status Card */}
      <div className="card" style={{ padding: '1rem', marginBottom: '1.25rem', background: isOverridden ? '#fffbeb' : '#f8fafc', borderLeft: isOverridden ? '4px solid #f59e0b' : '4px solid var(--color-primary-600)' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
          <span style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--color-text-muted)', textTransform: 'uppercase' }}>
            Decision Alignment
          </span>
          <span className={`badge ${alignment === 'ALIGNED' ? 'badge-low' : alignment === 'OVERRIDDEN' ? 'badge-medium' : 'badge-neutral'}`} style={{ fontSize: '0.75rem' }}>
            {alignment}
          </span>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem', marginTop: '0.5rem', fontSize: '0.8rem' }}>
          <div>
            <div style={{ color: 'var(--color-text-muted)' }}>AI Recommendation</div>
            <div style={{ fontWeight: 600, color: 'var(--color-text-primary)', marginTop: '2px' }}>
              {(historyData?.ai_recommendation || 'NOT_REVIEWED').replace(/_/g, ' ')}
            </div>
          </div>
          <div>
            <div style={{ color: 'var(--color-text-muted)' }}>Human Decision</div>
            <div style={{ fontWeight: 600, color: 'var(--color-text-primary)', marginTop: '2px' }}>
              {(historyData?.human_decision || 'PENDING').replace(/_/g, ' ')}
            </div>
          </div>
        </div>

        {isOverridden && (
          <div style={{ marginTop: '0.75rem', paddingTop: '0.6rem', borderTop: '1px solid #fde68a', fontSize: '0.75rem', color: '#92400e' }}>
            <strong>Override Justification:</strong> {historyData?.override_reason || 'Human officer override documented in audit trail.'}
          </div>
        )}
      </div>

      {/* Audit Timeline */}
      <div style={{ marginBottom: '1.5rem' }}>
        <h4 style={{ fontSize: '0.8rem', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.04em', color: 'var(--color-text-muted)', marginBottom: '0.75rem' }}>
          Audit Trail ({auditEvents.length})
        </h4>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.65rem' }}>
          {auditEvents.length === 0 ? (
            <div style={{ padding: '1rem', textAlign: 'center', color: 'var(--color-text-muted)', fontSize: '0.825rem' }}>
              No audit events recorded yet.
            </div>
          ) : (
            auditEvents.map((ev, i) => (
              <div
                key={i}
                style={{
                  padding: '0.75rem 0.85rem',
                  background: '#ffffff',
                  border: '1px solid var(--color-border)',
                  borderRadius: 'var(--radius-md)',
                  fontSize: '0.8rem',
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.35rem' }}>
                  <span style={{ fontWeight: 600, color: 'var(--color-text-primary)' }}>
                    {ev.action?.replace(/_/g, ' ') || 'Event'}
                  </span>
                  <span style={{ fontSize: '0.725rem', color: 'var(--color-text-muted)' }}>
                    {formatDateTime(ev.timestamp)}
                  </span>
                </div>
                <div style={{ fontSize: '0.75rem', color: 'var(--color-text-secondary)' }}>
                  Officer: <strong>{ev.officer_id || ev.actor_id || 'Officer'}</strong>
                </div>
                {ev.notes && (
                  <div style={{ marginTop: '0.35rem', padding: '0.4rem 0.6rem', background: '#f8fafc', borderRadius: 'var(--radius-sm)', fontSize: '0.725rem', color: 'var(--color-text-muted)' }}>
                    "{ev.notes}"
                  </div>
                )}
              </div>
            ))
          )}
        </div>
      </div>

      {/* Officer Feedback */}
      {feedbackList.length > 0 && (
        <div>
          <h4 style={{ fontSize: '0.8rem', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.04em', color: 'var(--color-text-muted)', marginBottom: '0.5rem' }}>
            Officer Feedback Notes
          </h4>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.4rem' }}>
            {feedbackList.map((fb, i) => (
              <div key={i} style={{ padding: '0.65rem 0.85rem', background: '#f8fafc', border: '1px solid var(--color-border)', borderRadius: 'var(--radius-md)', fontSize: '0.775rem' }}>
                <div style={{ fontWeight: 600, color: 'var(--color-text-primary)', marginBottom: '0.2rem' }}>
                  {fb.category || 'General Feedback'}
                </div>
                <div style={{ color: 'var(--color-text-secondary)' }}>{fb.feedback}</div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
