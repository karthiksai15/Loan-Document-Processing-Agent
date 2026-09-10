import React from 'react';
import { ShieldCheck, TrendingUp, AlertCircle, Grid } from 'lucide-react';
import { RiskBadge, PriorityBadge, StatusBadge, QualityBadge } from '../Common/Badges';
import { formatPercent } from '../../services/formatters';

export function ReviewSummaryMatrix({ reviewScore, riskData }) {
  const mlScore = reviewScore?.ml_risk_score ?? riskData?.rejection_probability;
  const mlLevel = reviewScore?.ml_risk_level ?? riskData?.risk_level ?? 'LOW';
  const evidenceScore = reviewScore?.evidence_trust_score ?? 100;
  const evidenceLevel = reviewScore?.evidence_trust_level ?? 'HIGH';
  const priority = reviewScore?.review_priority ?? 'LOW';
  const matrixCat = reviewScore?.risk_evidence_matrix_category ?? (priority === 'HIGH' ? 'INVESTIGATE' : 'CLEAN');

  return (
    <div style={{ marginBottom: '1.25rem' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.75rem' }}>
        <h3 style={{ fontSize: '0.9rem', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--color-text-muted)' }}>
          Review Intelligence Matrix
        </h3>
        <span style={{ fontSize: '0.75rem', color: 'var(--color-text-muted)' }}>
          Multi-layer deterministic & ML scoring
        </span>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '1rem' }}>
        {/* ML Historical Risk */}
        <div className="card" style={{ padding: '1.25rem', borderLeft: mlLevel === 'HIGH' ? '4px solid var(--color-danger-border)' : '4px solid var(--color-border)' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
            <span style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--color-text-muted)', textTransform: 'uppercase' }}>
              Historical Rejection Risk
            </span>
            <TrendingUp size={16} color="var(--color-primary-600)" />
          </div>
          <div style={{ display: 'flex', alignItems: 'baseline', gap: '0.75rem', marginBottom: '0.35rem' }}>
            <span style={{ fontSize: '1.75rem', fontWeight: 700, color: 'var(--color-text-primary)' }}>
              {formatPercent(mlScore)}
            </span>
            <RiskBadge level={mlLevel} />
          </div>
          <p style={{ fontSize: '0.725rem', color: 'var(--color-text-muted)', lineHeight: 1.35 }}>
            ML statistical estimate based on historical loan outcomes. <em>Does not approve or reject loans.</em>
          </p>
        </div>

        {/* Evidence Quality */}
        <div className="card" style={{ padding: '1.25rem', borderLeft: evidenceLevel === 'LOW' ? '4px solid var(--color-danger-border)' : '4px solid var(--color-border)' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
            <span style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--color-text-muted)', textTransform: 'uppercase' }}>
              Evidence Quality
            </span>
            <ShieldCheck size={16} color="var(--color-primary-600)" />
          </div>
          <div style={{ display: 'flex', alignItems: 'baseline', gap: '0.75rem', marginBottom: '0.35rem' }}>
            <span style={{ fontSize: '1.75rem', fontWeight: 700, color: 'var(--color-text-primary)' }}>
              {Math.round(evidenceScore)}/100
            </span>
            <QualityBadge level={evidenceLevel} />
          </div>
          <p style={{ fontSize: '0.725rem', color: 'var(--color-text-muted)', lineHeight: 1.35 }}>
            Derived from cross-document consistency, KYC matching, and mathematical validation checks.
          </p>
        </div>

        {/* Review Priority */}
        <div className="card" style={{ padding: '1.25rem', borderLeft: priority === 'HIGH' ? '4px solid var(--color-danger-border)' : priority === 'MEDIUM' ? '4px solid var(--color-warning-border)' : '4px solid var(--color-border)' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
            <span style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--color-text-muted)', textTransform: 'uppercase' }}>
              Review Priority
            </span>
            <AlertCircle size={16} color="var(--color-primary-600)" />
          </div>
          <div style={{ display: 'flex', alignItems: 'baseline', gap: '0.75rem', marginBottom: '0.35rem' }}>
            <span style={{ fontSize: '1.75rem', fontWeight: 700, color: 'var(--color-text-primary)' }}>
              {reviewScore?.review_score !== undefined ? `${Math.round(reviewScore.review_score)}/100` : priority}
            </span>
            <PriorityBadge priority={priority} />
          </div>
          <p style={{ fontSize: '0.725rem', color: 'var(--color-text-muted)', lineHeight: 1.35 }}>
            Calculated urgency for loan officer investigation based on severity of detected discrepancies.
          </p>
        </div>

        {/* Risk / Evidence Matrix Category */}
        <div className="card" style={{ padding: '1.25rem', borderLeft: matrixCat === 'INVESTIGATE' ? '4px solid #b91c1c' : matrixCat === 'REVIEW' ? '4px solid #b45309' : '4px solid #15803d' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
            <span style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--color-text-muted)', textTransform: 'uppercase' }}>
              Action Matrix
            </span>
            <Grid size={16} color="var(--color-primary-600)" />
          </div>
          <div style={{ display: 'flex', alignItems: 'baseline', gap: '0.75rem', marginBottom: '0.35rem' }}>
            <span style={{ fontSize: '1.35rem', fontWeight: 700, color: 'var(--color-text-primary)' }}>
              {matrixCat}
            </span>
            <StatusBadge status={matrixCat} />
          </div>
          <p style={{ fontSize: '0.725rem', color: 'var(--color-text-muted)', lineHeight: 1.35 }}>
            {matrixCat === 'INVESTIGATE'
              ? 'Critical mismatch detected. Detailed manual officer verification is required.'
              : matrixCat === 'REVIEW'
              ? 'Minor warnings or missing follow-ups detected. Standard officer inspection.'
              : 'Clean application. Verified evidence and consistent documentation.'}
          </p>
        </div>
      </div>
    </div>
  );
}
