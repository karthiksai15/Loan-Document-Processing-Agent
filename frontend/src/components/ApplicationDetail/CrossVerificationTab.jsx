import React from 'react';
import { CheckCircle2, AlertTriangle, GitCompare, ArrowRight } from 'lucide-react';
import { StatusBadge } from '../Common/Badges';
import { maskDocumentText } from '../../services/masking';

export function CrossVerificationTab({ verificationData }) {
  if (!verificationData) {
    return (
      <div className="card" style={{ padding: '2rem', textAlign: 'center', color: 'var(--color-text-muted)' }}>
        Verification has not been executed for this application yet.
      </div>
    );
  }

  const findings = verificationData.findings || [];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
      {/* Verification Overview Metric Bar */}
      <div className="card" style={{ padding: '1.25rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '1rem' }}>
          <div>
            <div style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--color-text-muted)', textTransform: 'uppercase' }}>
              Verification Status
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginTop: '0.25rem' }}>
              <StatusBadge status={verificationData.overall_result || verificationData.status} />
              <span style={{ fontSize: '0.85rem', color: 'var(--color-text-secondary)' }}>
                {verificationData.summary || `${verificationData.matched_comparisons} of ${verificationData.total_comparisons} comparisons matched`}
              </span>
            </div>
          </div>

          <div style={{ display: 'flex', gap: '1.5rem', textAlign: 'center' }}>
            <div>
              <div style={{ fontSize: '1.25rem', fontWeight: 700, color: '#15803d' }}>
                {verificationData.matched_comparisons}
              </div>
              <div style={{ fontSize: '0.7rem', color: 'var(--color-text-muted)', textTransform: 'uppercase' }}>
                Matched
              </div>
            </div>
            <div>
              <div style={{ fontSize: '1.25rem', fontWeight: 700, color: '#b91c1c' }}>
                {verificationData.mismatched_comparisons}
              </div>
              <div style={{ fontSize: '0.7rem', color: 'var(--color-text-muted)', textTransform: 'uppercase' }}>
                Mismatches
              </div>
            </div>
            <div>
              <div style={{ fontSize: '1.25rem', fontWeight: 700, color: '#b45309' }}>
                {verificationData.warning_count}
              </div>
              <div style={{ fontSize: '0.7rem', color: 'var(--color-text-muted)', textTransform: 'uppercase' }}>
                Warnings
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Findings Comparison List */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
        {findings.map((f, i) => {
          const isMismatch = f.result === 'MISMATCH';
          return (
            <div
              key={i}
              className="card"
              style={{
                borderLeft: isMismatch ? '4px solid var(--color-danger-border)' : '4px solid var(--color-success-border)',
                padding: '1.25rem',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.75rem', flexWrap: 'wrap', gap: '0.5rem' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                  {isMismatch ? (
                    <AlertTriangle size={18} color="var(--color-danger-text)" />
                  ) : (
                    <CheckCircle2 size={18} color="var(--color-success-text)" />
                  )}
                  <h4 style={{ fontSize: '0.95rem', fontWeight: 600, color: isMismatch ? 'var(--color-danger-text)' : 'var(--color-text-primary)' }}>
                    {f.rule_name}
                  </h4>
                  <span className="badge badge-neutral" style={{ fontSize: '0.675rem' }}>
                    {f.verification_type.replace(/_/g, ' ')}
                  </span>
                </div>

                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                  <span className={`badge ${f.severity === 'ERROR' ? 'badge-high' : f.severity === 'WARNING' ? 'badge-medium' : 'badge-info'}`} style={{ fontSize: '0.675rem' }}>
                    {f.severity}
                  </span>
                  <StatusBadge status={f.result} />
                </div>
              </div>

              {/* Side by side Source A vs Source B */}
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '1rem', background: 'var(--color-bg-subtle)', padding: '1rem', borderRadius: 'var(--radius-md)', marginBottom: '0.75rem' }}>
                <div>
                  <span style={{ fontSize: '0.725rem', fontWeight: 600, color: 'var(--color-text-muted)', textTransform: 'uppercase' }}>
                    Source A: {f.source_a}
                  </span>
                  <div style={{ fontSize: '0.8rem', color: 'var(--color-text-secondary)', marginBottom: '0.2rem' }}>
                    Field: <code>{f.field_a}</code>
                  </div>
                  <div style={{ fontSize: '1rem', fontWeight: 600, color: 'var(--color-text-primary)' }}>
                    {maskDocumentText(f.value_a) || '—'}
                  </div>
                </div>

                <div>
                  <span style={{ fontSize: '0.725rem', fontWeight: 600, color: isMismatch ? 'var(--color-danger-text)' : 'var(--color-text-muted)', textTransform: 'uppercase' }}>
                    Source B: {f.source_b}
                  </span>
                  <div style={{ fontSize: '0.8rem', color: 'var(--color-text-secondary)', marginBottom: '0.2rem' }}>
                    Field: <code>{f.field_b}</code>
                  </div>
                  <div style={{ fontSize: '1rem', fontWeight: 600, color: isMismatch ? 'var(--color-danger-text)' : 'var(--color-text-primary)' }}>
                    {maskDocumentText(f.value_b) || '—'}
                  </div>
                </div>

                {f.difference_percent !== null && f.difference_percent !== undefined && (
                  <div>
                    <span style={{ fontSize: '0.725rem', fontWeight: 600, color: 'var(--color-text-muted)', textTransform: 'uppercase' }}>
                      Discrepancy Metrics
                    </span>
                    <div style={{ fontSize: '0.8rem', color: 'var(--color-text-secondary)', marginBottom: '0.2rem' }}>
                      Allowed Tolerance: {f.tolerance_percent || 0}%
                    </div>
                    <div style={{ fontSize: '1rem', fontWeight: 700, color: isMismatch ? 'var(--color-danger-text)' : 'var(--color-success-text)' }}>
                      Difference: {f.difference_percent.toFixed(1)}%
                    </div>
                  </div>
                )}
              </div>

              <p style={{ fontSize: '0.85rem', color: isMismatch ? 'var(--color-danger-text)' : 'var(--color-text-secondary)' }}>
                {f.message}
              </p>
            </div>
          );
        })}
      </div>
    </div>
  );
}
