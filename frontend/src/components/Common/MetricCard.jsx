import React from 'react';

export function MetricCard({ title, value, subtitle, icon: Icon, badge, highlight, onClick }) {
  let borderClass = 'var(--color-border)';
  if (highlight === 'danger') borderClass = 'var(--color-danger-border)';
  if (highlight === 'warning') borderClass = 'var(--color-warning-border)';
  if (highlight === 'success') borderClass = 'var(--color-success-border)';

  return (
    <div
      className="card"
      style={{
        padding: '1.25rem',
        borderLeft: highlight ? `4px solid ${borderClass}` : undefined,
        cursor: onClick ? 'pointer' : 'default',
        transition: 'transform 0.15s ease, box-shadow 0.15s ease',
      }}
      onClick={onClick}
    >
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
        <span style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--color-text-muted)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
          {title}
        </span>
        {Icon && (
          <div style={{ color: 'var(--color-primary-600)', background: 'var(--color-primary-50)', padding: '6px', borderRadius: 'var(--radius-md)' }}>
            <Icon size={18} />
          </div>
        )}
      </div>
      <div style={{ display: 'flex', alignItems: 'baseline', gap: '0.75rem', marginBottom: '0.25rem' }}>
        <span style={{ fontSize: '1.75rem', fontWeight: 700, color: 'var(--color-text-primary)' }}>
          {value}
        </span>
        {badge}
      </div>
      {subtitle && (
        <div style={{ fontSize: '0.775rem', color: 'var(--color-text-secondary)' }}>
          {subtitle}
        </div>
      )}
    </div>
  );
}
