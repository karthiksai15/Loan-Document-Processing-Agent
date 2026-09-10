import React from 'react';
import { AlertCircle, RefreshCw } from 'lucide-react';

export function ErrorAlert({ message, onRetry, title = 'Unable to load data' }) {
  return (
    <div
      style={{
        padding: '1.25rem',
        borderRadius: 'var(--radius-lg)',
        border: '1px solid var(--color-danger-border)',
        backgroundColor: 'var(--color-danger-bg)',
        color: 'var(--color-danger-text)',
        display: 'flex',
        alignItems: 'flex-start',
        gap: '0.875rem',
        margin: '1rem 0',
      }}
    >
      <AlertCircle size={20} style={{ flexShrink: 0, marginTop: '2px' }} />
      <div style={{ flex: 1 }}>
        <h4 style={{ color: 'var(--color-danger-text)', marginBottom: '0.25rem', fontSize: '0.9rem' }}>
          {title}
        </h4>
        <p style={{ color: 'var(--color-danger-text)', fontSize: '0.825rem', opacity: 0.9, marginBottom: onRetry ? '0.75rem' : 0 }}>
          {message || 'The server encountered an error. Please verify the backend connection and try again.'}
        </p>
        {onRetry && (
          <button
            type="button"
            className="btn btn-sm btn-outline-danger"
            onClick={onRetry}
            style={{ display: 'inline-flex', alignItems: 'center', gap: '0.35rem' }}
          >
            <RefreshCw size={12} />
            <span>Retry</span>
          </button>
        )}
      </div>
    </div>
  );
}
