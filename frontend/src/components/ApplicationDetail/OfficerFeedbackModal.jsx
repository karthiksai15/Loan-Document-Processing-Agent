import React, { useState } from 'react';
import { MessageSquare, X } from 'lucide-react';

export function OfficerFeedbackModal({ isOpen, onClose, onSubmit, submitting }) {
  const [category, setCategory] = useState('CORRECT');
  const [feedback, setFeedback] = useState('');
  const [error, setError] = useState('');

  React.useEffect(() => {
    if (isOpen) {
      setFeedback('');
      setError('');
      setCategory('CORRECT');
    }
  }, [isOpen]);

  if (!isOpen) return null;

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!feedback.trim()) {
      setError('Please provide feedback comments.');
      return;
    }

    onSubmit({
      officerId: 'loan_officer_001',
      category,
      feedback: feedback.trim(),
    });
  };

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <MessageSquare size={20} color="var(--color-primary-600)" />
            <h3 style={{ fontSize: '1.05rem', fontWeight: 600 }}>
              Submit Officer Feedback
            </h3>
          </div>
          <button type="button" className="btn btn-sm btn-secondary" onClick={onClose} style={{ padding: '4px' }}>
            <X size={16} />
          </button>
        </div>

        <form onSubmit={handleSubmit}>
          <div className="modal-body">
            <p style={{ fontSize: '0.825rem', color: 'var(--color-text-secondary)', marginBottom: '1rem' }}>
              Evaluate the accuracy of the AI recommendation and automated evidence extraction to support model governance.
            </p>

            <div className="form-group">
              <label className="form-label" htmlFor="feedback-category-select">
                Evaluation Category:
              </label>
              <select
                id="feedback-category-select"
                className="form-select"
                value={category}
                onChange={(e) => setCategory(e.target.value)}
              >
                <option value="CORRECT">CORRECT — AI findings and recommendations were accurate</option>
                <option value="PARTIALLY_CORRECT">PARTIALLY_CORRECT — Useful signals, but minor gaps detected</option>
                <option value="INCORRECT">INCORRECT — AI false positive or erroneous flag</option>
                <option value="NOT_APPLICABLE">NOT_APPLICABLE — Exception or out-of-scope scenario</option>
              </select>
            </div>

            <div className="form-group">
              <label className="form-label" htmlFor="feedback-text-input">
                Officer Commentary & Critique:
              </label>
              <textarea
                id="feedback-text-input"
                className="form-textarea"
                placeholder="Describe your assessment of the AI investigation quality..."
                value={feedback}
                onChange={(e) => setFeedback(e.target.value)}
                rows={3}
                required
              />
            </div>

            {error && (
              <div style={{ color: '#b91c1c', fontSize: '0.8rem', fontWeight: 500, marginBottom: '0.5rem' }}>
                {error}
              </div>
            )}
          </div>

          <div className="modal-footer">
            <button type="button" className="btn btn-secondary" onClick={onClose} disabled={submitting}>
              Cancel
            </button>
            <button type="submit" className="btn btn-primary" disabled={submitting}>
              {submitting ? 'Submitting Feedback...' : 'Save Officer Feedback'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
