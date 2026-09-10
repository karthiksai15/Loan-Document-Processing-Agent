import React from 'react';
import { AlertTriangle, CheckCircle2, ArrowRight } from 'lucide-react';

export function AttentionBanner({ reviewScore, verificationData, humanReview, onSelectTab }) {
  const primaryReason = reviewScore?.primary_reason;
  const secondaryReasons = reviewScore?.secondary_reasons || [];
  const findings = verificationData?.findings || [];
  const reasons = humanReview?.reasons || [];

  // Look for high-severity mismatch in findings
  const mismatchFinding = findings.find(
    (f) => f.result === 'MISMATCH' && (f.severity === 'ERROR' || f.verification_type.includes('IDENTITY'))
  );

  const isClean =
    (!primaryReason || primaryReason.toLowerCase().includes('clean') || primaryReason.toLowerCase().includes('standard')) &&
    !mismatchFinding &&
    reasons.length === 0;

  if (isClean) {
    return (
      <div className="attention-banner clean">
        <div style={{ color: 'var(--color-success-text)', marginTop: '2px' }}>
          <CheckCircle2 size={22} />
        </div>
        <div style={{ flex: 1 }}>
          <h4 style={{ color: 'var(--color-success-text)', fontSize: '0.95rem', marginBottom: '0.25rem', fontWeight: 600 }}>
            Standard Application — No Critical Discrepancies
          </h4>
          <p style={{ color: 'var(--color-success-text)', fontSize: '0.85rem', opacity: 0.9 }}>
            All cross-document comparisons match verified applicant data. High evidence trust score and clean verification profile.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="attention-banner danger">
      <div style={{ color: 'var(--color-danger-text)', marginTop: '2px' }}>
        <AlertTriangle size={24} />
      </div>
      <div style={{ flex: 1 }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '0.5rem', marginBottom: '0.35rem' }}>
          <h4 style={{ color: 'var(--color-danger-text)', fontSize: '1rem', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.02em' }}>
            Why Does This Application Need Attention?
          </h4>
          {onSelectTab && (
            <button
              type="button"
              className="btn btn-sm"
              onClick={() => onSelectTab(mismatchFinding ? 'verification' : 'evidence')}
              style={{
                backgroundColor: 'rgba(255, 255, 255, 0.8)',
                color: 'var(--color-danger-text)',
                border: '1px solid var(--color-danger-border)',
                fontWeight: 600,
              }}
            >
              <span>View Supporting Evidence</span>
              <ArrowRight size={14} />
            </button>
          )}
        </div>

        {/* Primary Alert Highlight */}
        <div style={{ backgroundColor: 'rgba(255, 255, 255, 0.65)', padding: '0.75rem 1rem', borderRadius: 'var(--radius-md)', border: '1px solid var(--color-danger-border)', marginBottom: '0.5rem' }}>
          <div style={{ fontWeight: 600, color: 'var(--color-danger-text)', fontSize: '0.9rem', marginBottom: '0.25rem' }}>
            {mismatchFinding ? mismatchFinding.rule_name : primaryReason || 'Discrepancy detected during validation'}
          </div>

          {mismatchFinding && (
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '0.75rem', marginTop: '0.5rem', fontSize: '0.85rem' }}>
              <div style={{ background: '#ffffff', padding: '0.5rem', borderRadius: 'var(--radius-sm)', border: '1px solid var(--color-border)' }}>
                <span style={{ color: 'var(--color-text-muted)', fontSize: '0.75rem', display: 'block' }}>
                  {mismatchFinding.source_a} ({mismatchFinding.field_a})
                </span>
                <strong style={{ color: 'var(--color-text-primary)' }}>{mismatchFinding.value_a || '—'}</strong>
              </div>
              <div style={{ background: '#ffffff', padding: '0.5rem', borderRadius: 'var(--radius-sm)', border: '1px solid var(--color-danger-border)' }}>
                <span style={{ color: 'var(--color-danger-text)', fontSize: '0.75rem', display: 'block' }}>
                  {mismatchFinding.source_b} ({mismatchFinding.field_b})
                </span>
                <strong style={{ color: 'var(--color-danger-text)' }}>{mismatchFinding.value_b || '—'}</strong>
              </div>
            </div>
          )}

          {mismatchFinding?.message && (
            <p style={{ marginTop: '0.5rem', fontSize: '0.825rem', color: 'var(--color-danger-text)' }}>
              {mismatchFinding.message}
            </p>
          )}
        </div>

        {/* Secondary reasons or Human Review gate reasons */}
        {(secondaryReasons.length > 0 || reasons.length > 0) && (
          <ul style={{ paddingLeft: '1.25rem', fontSize: '0.825rem', color: 'var(--color-danger-text)' }}>
            {reasons.map((r, i) => (
              <li key={i} style={{ marginBottom: '0.2rem' }}>
                <strong>{r.code}:</strong> {r.description}
              </li>
            ))}
            {secondaryReasons.map((s, i) => (
              <li key={`sec-${i}`} style={{ marginBottom: '0.2rem' }}>
                {s}
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
