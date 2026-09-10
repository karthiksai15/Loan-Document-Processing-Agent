import React from 'react';
import { GitCompareArrows, CheckCircle2, AlertTriangle, AlertCircle } from 'lucide-react';

export function CrossVerificationDrawer({ verificationData }) {
  const findings = verificationData?.findings || [];
  const total = verificationData?.total_comparisons || findings.length;
  const matches = verificationData?.matched_comparisons || findings.filter((f) => f.result === 'MATCH').length;
  const mismatches = verificationData?.mismatched_comparisons || findings.filter((f) => f.result === 'MISMATCH').length;

  return (
    <div className="verification-drawer-wrap">
      {/* Summary Matrix Box */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(3, 1fr)',
          gap: '0.75rem',
          padding: '0.85rem',
          background: '#f8fafc',
          border: '1px solid var(--color-border)',
          borderRadius: 'var(--radius-md)',
          marginBottom: '1.25rem',
          textAlign: 'center',
        }}
      >
        <div>
          <div style={{ fontSize: '0.7rem', color: 'var(--color-text-muted)', textTransform: 'uppercase', fontWeight: 600 }}>Total Checks</div>
          <div style={{ fontSize: '1.25rem', fontWeight: 700, color: 'var(--color-text-primary)' }}>{total}</div>
        </div>
        <div>
          <div style={{ fontSize: '0.7rem', color: '#166534', textTransform: 'uppercase', fontWeight: 600 }}>Matched</div>
          <div style={{ fontSize: '1.25rem', fontWeight: 700, color: '#16a34a' }}>{matches}</div>
        </div>
        <div>
          <div style={{ fontSize: '0.7rem', color: '#991b1b', textTransform: 'uppercase', fontWeight: 600 }}>Mismatched</div>
          <div style={{ fontSize: '1.25rem', fontWeight: 700, color: mismatches > 0 ? '#dc2626' : '#16a34a' }}>{mismatches}</div>
        </div>
      </div>

      {/* Comparisons List */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
        {findings.length === 0 ? (
          <div style={{ padding: '1.5rem', textAlign: 'center', color: 'var(--color-text-muted)' }}>
            No verification findings available.
          </div>
        ) : (
          findings.map((finding, idx) => {
            const isMatch = finding.result === 'MATCH';
            const isError = finding.severity === 'ERROR';
            const typeLabel = (finding.verification_type || '').replace(/_/g, ' ');

            return (
              <div
                key={idx}
                style={{
                  padding: '1rem',
                  background: isMatch ? '#ffffff' : isError ? '#fef2f2' : '#fffbeb',
                  border: isMatch ? '1px solid var(--color-border)' : isError ? '1px solid #fecaca' : '1px solid #fde68a',
                  borderRadius: 'var(--radius-md)',
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.4rem' }}>
                  <span style={{ fontSize: '0.7rem', fontWeight: 700, color: 'var(--color-text-muted)', textTransform: 'uppercase' }}>
                    {typeLabel}
                  </span>
                  <span className={`badge ${isMatch ? 'badge-low' : isError ? 'badge-high' : 'badge-medium'}`} style={{ fontSize: '0.7rem' }}>
                    {finding.result}
                  </span>
                </div>

                <div style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--color-text-primary)', marginBottom: '0.5rem' }}>
                  {finding.message}
                </div>

                {/* Side-by-side values comparison */}
                <div
                  style={{
                    display: 'grid',
                    gridTemplateColumns: '1fr 1fr',
                    gap: '0.5rem',
                    padding: '0.5rem 0.75rem',
                    background: '#ffffff',
                    border: '1px solid var(--color-border)',
                    borderRadius: 'var(--radius-sm)',
                    fontSize: '0.75rem',
                  }}
                >
                  <div>
                    <div style={{ color: 'var(--color-text-muted)', fontWeight: 500 }}>{finding.source_a} ({finding.field_a})</div>
                    <div style={{ fontWeight: 600, color: 'var(--color-text-primary)', marginTop: '2px', fontFamily: 'var(--font-mono)' }}>
                      {String(finding.value_a)}
                    </div>
                  </div>
                  <div>
                    <div style={{ color: 'var(--color-text-muted)', fontWeight: 500 }}>{finding.source_b} ({finding.field_b})</div>
                    <div style={{ fontWeight: 600, color: isMatch ? 'var(--color-text-primary)' : '#b91c1c', marginTop: '2px', fontFamily: 'var(--font-mono)' }}>
                      {String(finding.value_b)}
                    </div>
                  </div>
                </div>

                {finding.evidence && (
                  <div style={{ marginTop: '0.4rem', fontSize: '0.725rem', color: 'var(--color-text-secondary)' }}>
                    Evidence: {finding.evidence}
                  </div>
                )}
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
