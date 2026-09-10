import React from 'react';
import { Link } from 'react-router-dom';
import { ArrowLeft } from 'lucide-react';
import { formatINR } from '../../services/formatters';
import { StatusBadge } from '../Common/Badges';

export function ApplicantHeader({ application, humanReview, reviewScore, mismatchFinding }) {
  if (!application) return null;

  const rawStatus = humanReview?.human_review_status || application.human_review_status || application.status || 'REQUIRED';
  const statusDisplay = rawStatus === 'REQUIRED' ? 'NEEDS REVIEW' : rawStatus.replace(/_/g, ' ');

  // Compute short reason from real verification findings and review assessment
  let shortReason = '';
  if (mismatchFinding) {
    if (mismatchFinding.verification_type?.includes('IDENTITY') || mismatchFinding.rule_name?.toLowerCase().includes('name')) {
      shortReason = 'Identity information does not match.';
    } else if (mismatchFinding.rule_name?.toLowerCase().includes('salary') || mismatchFinding.rule_name?.toLowerCase().includes('income')) {
      shortReason = 'Income details differ between payslip and bank statement.';
    } else {
      shortReason = mismatchFinding.message || 'Cross-document discrepancy detected.';
    }
  } else if (reviewScore?.primary_reason) {
    shortReason = reviewScore.primary_reason;
  } else if (rawStatus === 'REQUIRED') {
    shortReason = 'Verification check requires human review.';
  } else {
    shortReason = 'All documentation verified and consistent.';
  }

  return (
    <div className="card" style={{ padding: '1.25rem 1.5rem', marginBottom: '0.5rem' }}>
      <div style={{ marginBottom: '0.75rem' }}>
        <Link
          to="/applications"
          style={{ display: 'inline-flex', alignItems: 'center', gap: '0.35rem', fontSize: '0.825rem', color: 'var(--color-text-muted)', fontWeight: 500 }}
        >
          <ArrowLeft size={16} />
          <span>Back to Applications</span>
        </Link>
      </div>

      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', flexWrap: 'wrap', gap: '1.25rem' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'baseline', gap: '0.75rem', marginBottom: '0.35rem' }}>
            <h1 style={{ fontSize: '1.65rem', fontWeight: 700, color: 'var(--color-text-primary)' }}>
              {application.applicant_name}
            </h1>
            <span style={{ fontSize: '0.9rem', color: 'var(--color-text-muted)', fontWeight: 600 }}>
              Application {application.application_id}
            </span>
          </div>

          <div style={{ display: 'flex', gap: '1.25rem', flexWrap: 'wrap', fontSize: '0.875rem', color: 'var(--color-text-secondary)', marginTop: '0.35rem' }}>
            <span>Loan Amount: <strong style={{ color: 'var(--color-text-primary)' }}>{formatINR(application.loan_amount)}</strong></span>
            {application.income_annum && (
              <span>Annual Income: <strong style={{ color: 'var(--color-text-primary)' }}>{formatINR(application.income_annum)}</strong></span>
            )}
            {application.cibil_score && (
              <span>CIBIL: <strong style={{ color: application.cibil_score >= 750 ? '#15803d' : application.cibil_score >= 650 ? '#b45309' : '#b91c1c' }}>{application.cibil_score}</strong></span>
            )}
            {application.employer && (
              <span>Employer: <strong>{application.employer}</strong></span>
            )}
          </div>
        </div>

        {/* Large Status & Short Reason */}
        <div style={{ textAlign: 'right', display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: '0.25rem' }}>
          <div style={{ fontSize: '1.1rem', fontWeight: 800 }}>
            <StatusBadge status={rawStatus} />
          </div>
          <p style={{ fontSize: '0.825rem', color: 'var(--color-danger-text)', fontWeight: 500, maxWidth: '280px', textAlign: 'right' }}>
            {shortReason}
          </p>
        </div>
      </div>
    </div>
  );
}

