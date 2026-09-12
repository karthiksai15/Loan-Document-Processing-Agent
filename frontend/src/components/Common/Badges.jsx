import React from 'react';

export function RiskBadge({ level, score }) {
  const lvl = (level || 'LOW').toUpperCase();
  let badgeClass = 'badge-low';
  let icon = '●';

  if (lvl === 'HIGH') {
    badgeClass = 'badge-high';
    icon = '▲';
  } else if (lvl === 'MEDIUM') {
    badgeClass = 'badge-medium';
    icon = '■';
  }

  return (
    <span className={`badge ${badgeClass}`} title={score !== undefined ? `Risk Score: ${score}` : undefined}>
      <span className="badge-dot" />
      <span>{lvl}</span>
      {score !== undefined && <span style={{ opacity: 0.85, fontSize: '0.7rem' }}>({typeof score === 'number' && score <= 1 ? `${(score * 100).toFixed(1)}%` : score})</span>}
    </span>
  );
}

export function PriorityBadge({ priority, score }) {
  const p = (priority || 'LOW').toUpperCase();
  let badgeClass = 'badge-low';

  if (p === 'HIGH') {
    badgeClass = 'badge-high';
  } else if (p === 'MEDIUM') {
    badgeClass = 'badge-medium';
  }

  return (
    <span className={`badge ${badgeClass}`}>
      <span className="badge-dot" />
      <span>{p}</span>
      {score !== undefined && <span style={{ opacity: 0.85, fontSize: '0.7rem' }}>({score}/100)</span>}
    </span>
  );
}

export function StatusBadge({ status }) {
  const s = (status || 'UNKNOWN').toUpperCase();
  let badgeClass = 'badge-neutral';

  switch (s) {
    case 'APPROVED':
    case 'COMPLETED':
    case 'GROUNDED':
    case 'SUFFICIENT':
    case 'MATCH':
    case 'PASS':
    case 'CLEAN':
      badgeClass = 'badge-low';
      break;
    case 'REQUIRED':
    case 'REJECTED':
    case 'ESCALATED':
    case 'FAILED':
    case 'ERROR':
    case 'MISMATCH':
    case 'MISMATCHES_FOUND':
    case 'UNGROUNDED':
      badgeClass = 'badge-high';
      break;
    case 'IN_REVIEW':
    case 'UNDER_REVIEW':
    case 'ADDITIONAL_DOCUMENTS_REQUIRED':
    case 'OVERRIDDEN':
    case 'WARNING':
    case 'PARTIAL':
    case 'REVIEW':
    case 'INVESTIGATE':
      badgeClass = 'badge-medium';
      break;
    case 'NOT_REQUIRED':
    case 'STANDARD_REVIEW':
    case 'SUBMITTED':
    case 'INFO':
      badgeClass = 'badge-info';
      break;
    default:
      badgeClass = 'badge-neutral';
  }

  return (
    <span className={`badge ${badgeClass}`}>
      <span className="badge-dot" />
      <span>{s.replace(/_/g, ' ')}</span>
    </span>
  );
}

export function ConfidenceBadge({ level, score }) {
  const lvl = (level || 'LOW').toUpperCase();
  let badgeClass = 'badge-high';

  if (lvl === 'HIGH') {
    badgeClass = 'badge-low';
  } else if (lvl === 'MEDIUM') {
    badgeClass = 'badge-medium';
  }

  return (
    <span className={`badge ${badgeClass}`} title="AI Review Confidence">
      <span className="badge-dot" />
      <span>{lvl}</span>
      {score !== undefined && (
        <span style={{ opacity: 0.85, fontSize: '0.7rem' }}>
          ({typeof score === 'number' && score <= 1 ? `${Math.round(score * 100)}%` : `${Math.round(score)}%`})
        </span>
      )}
    </span>
  );
}

export function QualityBadge({ level, score }) {
  const lvl = (level || 'LOW').toUpperCase();
  let badgeClass = 'badge-high'; // LOW quality is flagged (red)

  if (lvl === 'HIGH') {
    badgeClass = 'badge-low'; // HIGH quality is good (green)
  } else if (lvl === 'MEDIUM') {
    badgeClass = 'badge-medium'; // MEDIUM quality is cautionary (amber)
  }

  return (
    <span className={`badge ${badgeClass}`} title={score !== undefined ? `Quality: ${score}` : undefined}>
      <span className="badge-dot" />
      <span>{lvl}</span>
      {score !== undefined && <span style={{ opacity: 0.85, fontSize: '0.7rem' }}>({score})</span>}
    </span>
  );
}
