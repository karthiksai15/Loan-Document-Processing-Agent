import React from 'react';
import { Gauge, AlertTriangle, ShieldCheck, HelpCircle } from 'lucide-react';
import { ConfidenceBadge } from '../Common/Badges';

export function ConfidenceTab({ humanReview }) {
  if (!humanReview) {
    return (
      <div className="card" style={{ padding: '2rem', textAlign: 'center', color: 'var(--color-text-muted)' }}>
        Confidence evaluation has not been performed for this application.
      </div>
    );
  }

  const score = humanReview.confidence_score;
  const level = humanReview.confidence_level;
  const factors = humanReview.confidence_factors || [];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
      {/* Top Confidence Metric Banner */}
      <div className="card" style={{ padding: '1.5rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '1rem' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.25rem' }}>
              <Gauge size={20} color="var(--color-primary-600)" />
              <h4 style={{ fontSize: '1rem', fontWeight: 600 }}>Deterministic AI Review Confidence</h4>
            </div>
            <p style={{ fontSize: '0.85rem', color: 'var(--color-text-secondary)' }}>
              A grounded, explainable scoring layer evaluating 7 weighted document factors and applying hard caps for critical risk conditions.
            </p>
          </div>

          <div style={{ display: 'flex', alignItems: 'baseline', gap: '0.75rem' }}>
            <span style={{ fontSize: '2.25rem', fontWeight: 800, color: 'var(--color-text-primary)' }}>
              {Math.round(score)}%
            </span>
            <ConfidenceBadge level={level} score={score} />
          </div>
        </div>

        {/* Informational Guidance */}
        <div style={{ marginTop: '1rem', padding: '0.75rem 1rem', background: 'var(--color-bg-subtle)', borderRadius: 'var(--radius-md)', border: '1px solid var(--color-border)', display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.8rem', color: 'var(--color-text-muted)' }}>
          <HelpCircle size={16} style={{ flexShrink: 0 }} />
          <span>
            <strong>Interpretation Guide:</strong> Review confidence measures certainty in the completeness and consistency of applicant documentation. A low score (e.g. 45%) means manual officer review is required due to data gaps or mismatches—it is <em>not</em> an estimate of applicant fraud.
          </span>
        </div>
      </div>

      {/* 7-Factor Breakdown Table */}
      <div className="card">
        <div className="card-header">
          <h4 style={{ fontSize: '0.9rem', fontWeight: 600 }}>Factor-by-Factor Explainability Breakdown</h4>
          <span style={{ fontSize: '0.75rem', color: 'var(--color-text-muted)' }}>
            Weights sum to 100%
          </span>
        </div>

        <div className="table-wrapper" style={{ border: 'none', borderRadius: 0 }}>
          <table className="data-table">
            <thead>
              <tr>
                <th>Factor</th>
                <th>Raw Score</th>
                <th>Weight</th>
                <th>Weighted Score</th>
                <th>Contribution</th>
                <th>Explainable Finding</th>
              </tr>
            </thead>
            <tbody>
              {factors.length > 0 ? (
                factors.map((f, idx) => (
                  <tr key={idx}>
                    <td style={{ fontWeight: 600, fontSize: '0.825rem' }}>
                      {(f.name || f.factor || '').replace(/_/g, ' ').toUpperCase()}
                    </td>
                    <td>
                      <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 600 }}>
                        {Math.round(f.score ?? f.raw_score ?? 0)}/100
                      </span>
                    </td>
                    <td style={{ color: 'var(--color-text-muted)', fontSize: '0.825rem' }}>
                      {f.weight ?? 0}%
                    </td>
                    <td style={{ fontFamily: 'var(--font-mono)', fontSize: '0.825rem' }}>
                      {(f.weighted_score ?? 0).toFixed(1)}
                    </td>
                    <td>
                      <span style={{ fontWeight: 600, color: 'var(--color-primary-700)' }}>
                        {(f.contribution_pct ?? (f.weighted_score || 0)).toFixed(1)}%
                      </span>
                    </td>
                    <td style={{ fontSize: '0.8rem', color: 'var(--color-text-secondary)', maxWidth: '300px' }}>
                      {f.explanation || f.description || '—'}
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={6} style={{ textAlign: 'center', padding: '2rem', color: 'var(--color-text-muted)' }}>
                    No breakdown factors available.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
