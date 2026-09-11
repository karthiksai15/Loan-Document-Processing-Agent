import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { ArrowLeft, Send, AlertCircle, Loader2, Building, ShieldCheck } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { api } from '../services/api';

export function CreateApplicationPage() {
  const { user } = useAuth();
  const navigate = useNavigate();

  const [formData, setFormData] = useState({
    applicant_name: user?.name || '',
    loan_amount: '',
    income_annum: '',
    employer: '',
    loan_term: 36,
    date_of_birth: '',
    address: '',
    education: 'Graduate',
    self_employed: 'No',
    notes: '',
  });

  const [submitting, setSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState(null);

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData((prev) => ({
      ...prev,
      [name]: value,
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setErrorMessage(null);

    const amount = parseFloat(formData.loan_amount);
    if (isNaN(amount) || amount <= 0) {
      setErrorMessage('Please enter a valid loan amount greater than ₹0.');
      return;
    }

    if (!formData.applicant_name.trim()) {
      setErrorMessage('Please enter your full legal name as it appears on your official KYC document.');
      return;
    }

    setSubmitting(true);

    try {
      const payload = {
        applicant_name: formData.applicant_name.trim(),
        loan_amount: amount,
        income_annum: formData.income_annum ? parseFloat(formData.income_annum) : null,
        employer: formData.employer.trim() || null,
        loan_term: parseInt(formData.loan_term, 10) || 36,
        date_of_birth: formData.date_of_birth || null,
        address: formData.address.trim() || null,
        education: formData.education,
        self_employed: formData.self_employed,
        notes: formData.notes.trim() || null,
      };

      const res = await api.createCustomerApplication(payload);
      if (res?.application_id) {
        navigate(`/customer/applications/${res.application_id}`);
      } else {
        navigate('/customer/dashboard');
      }
    } catch (err) {
      setErrorMessage(
        err?.message || 'Failed to initialize loan application. Please check your network and try again.'
      );
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="cust-create-app-container">
      <Link to="/customer/dashboard" className="cust-back-link">
        <ArrowLeft size={16} />
        <span>Back to My Applications</span>
      </Link>

      <div className="cust-form-card">
        <div className="cust-form-header">
          <div className="cust-form-badge">
            <Building size={24} color="#2563eb" />
          </div>
          <div>
            <h1 className="cust-form-title">Create Loan Application</h1>
            <p className="cust-form-desc">
              Fill in your profile details to initiate underwriting. A bank application number (GEN-YYYY-XXXXXX) will be generated automatically.
            </p>
          </div>
        </div>

        {errorMessage && (
          <div className="cust-error-banner" role="alert">
            <AlertCircle size={18} className="flex-shrink-0" />
            <span>{errorMessage}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="cust-form">
          <div className="cust-form-grid">
            {/* Full Legal Name */}
            <div className="cust-form-group">
              <label htmlFor="applicant_name" className="cust-label">
                Full Legal Name <span className="text-required">*</span>
              </label>
              <input
                type="text"
                id="applicant_name"
                name="applicant_name"
                value={formData.applicant_name}
                onChange={handleChange}
                placeholder="e.g. Rohan Verma"
                required
                className="cust-input"
              />
              <span className="cust-hint">Must match your Government PAN / Aadhaar KYC.</span>
            </div>

            {/* Requested Principal Loan Amount */}
            <div className="cust-form-group">
              <label htmlFor="loan_amount" className="cust-label">
                Requested Loan Amount (₹) <span className="text-required">*</span>
              </label>
              <input
                type="number"
                id="loan_amount"
                name="loan_amount"
                value={formData.loan_amount}
                onChange={handleChange}
                placeholder="e.g. 500000"
                min="1000"
                step="1000"
                required
                className="cust-input"
              />
            </div>

            {/* Gross Annual Income */}
            <div className="cust-form-group">
              <label htmlFor="income_annum" className="cust-label">
                Gross Annual Income (₹)
              </label>
              <input
                type="number"
                id="income_annum"
                name="income_annum"
                value={formData.income_annum}
                onChange={handleChange}
                placeholder="e.g. 1200000"
                min="0"
                step="5000"
                className="cust-input"
              />
              <span className="cust-hint">As reflected on your recent Tax Return or Form 16.</span>
            </div>

            {/* Employer / Business Name */}
            <div className="cust-form-group">
              <label htmlFor="employer" className="cust-label">
                Current Employer / Organization
              </label>
              <input
                type="text"
                id="employer"
                name="employer"
                value={formData.employer}
                onChange={handleChange}
                placeholder="e.g. Tata Consultancy Services"
                className="cust-input"
              />
            </div>

            {/* Loan Term */}
            <div className="cust-form-group">
              <label htmlFor="loan_term" className="cust-label">
                Loan Tenure (Months)
              </label>
              <select
                id="loan_term"
                name="loan_term"
                value={formData.loan_term}
                onChange={handleChange}
                className="cust-select"
              >
                <option value={12}>12 Months (1 Year)</option>
                <option value={24}>24 Months (2 Years)</option>
                <option value={36}>36 Months (3 Years)</option>
                <option value={48}>48 Months (4 Years)</option>
                <option value={60}>60 Months (5 Years)</option>
                <option value={84}>84 Months (7 Years)</option>
                <option value={120}>120 Months (10 Years)</option>
              </select>
            </div>

            {/* Date of Birth */}
            <div className="cust-form-group">
              <label htmlFor="date_of_birth" className="cust-label">
                Date of Birth
              </label>
              <input
                type="date"
                id="date_of_birth"
                name="date_of_birth"
                value={formData.date_of_birth}
                onChange={handleChange}
                className="cust-input"
              />
            </div>

            {/* Education */}
            <div className="cust-form-group">
              <label htmlFor="education" className="cust-label">
                Highest Education
              </label>
              <select
                id="education"
                name="education"
                value={formData.education}
                onChange={handleChange}
                className="cust-select"
              >
                <option value="Graduate">Graduate</option>
                <option value="Not Graduate">Not Graduate</option>
                <option value="Post Graduate">Post Graduate</option>
                <option value="Doctorate">Doctorate / Professional</option>
              </select>
            </div>

            {/* Self-employed */}
            <div className="cust-form-group">
              <label htmlFor="self_employed" className="cust-label">
                Self Employed?
              </label>
              <select
                id="self_employed"
                name="self_employed"
                value={formData.self_employed}
                onChange={handleChange}
                className="cust-select"
              >
                <option value="No">No (Salaried Employee)</option>
                <option value="Yes">Yes (Business / Freelance)</option>
              </select>
            </div>
          </div>

          {/* Current Address */}
          <div className="cust-form-group mt-3">
            <label htmlFor="address" className="cust-label">
              Residential Address
            </label>
            <textarea
              id="address"
              name="address"
              value={formData.address}
              onChange={handleChange}
              placeholder="Full residential address including city, state, and pin code"
              rows={2}
              className="cust-textarea"
            />
          </div>

          {/* Loan Purpose / Remarks */}
          <div className="cust-form-group mt-3">
            <label htmlFor="notes" className="cust-label">
              Loan Purpose / Remarks
            </label>
            <textarea
              id="notes"
              name="notes"
              value={formData.notes}
              onChange={handleChange}
              placeholder="e.g. Home improvement, medical expense, business expansion..."
              rows={2}
              className="cust-textarea"
            />
          </div>

          <div className="cust-form-footer">
            <div className="cust-form-disclaimer">
              <ShieldCheck size={16} color="#059669" />
              <span>
                Your data is stored securely in compliance with RBI underwriting guidelines.
              </span>
            </div>

            <div className="cust-form-actions">
              <Link to="/customer/dashboard" className="cust-cancel-btn">
                Cancel
              </Link>
              <button
                type="submit"
                disabled={submitting}
                className="cust-submit-btn"
              >
                {submitting ? (
                  <>
                    <Loader2 size={16} className="animate-spin" />
                    <span>Creating Application...</span>
                  </>
                ) : (
                  <>
                    <span>Next: Upload Documents</span>
                    <Send size={16} />
                  </>
                )}
              </button>
            </div>
          </div>
        </form>
      </div>

      <style>{`
        .cust-create-app-container {
          max-width: 800px;
          margin: 0 auto;
          display: flex;
          flex-direction: column;
          gap: 1.5rem;
        }

        .cust-back-link {
          display: inline-flex;
          align-items: center;
          gap: 0.375rem;
          color: #64748b;
          font-size: 0.875rem;
          font-weight: 500;
          text-decoration: none;
          transition: color 0.15s ease;
        }

        .cust-back-link:hover {
          color: #1e3a8a;
        }

        .cust-form-card {
          background: #ffffff;
          border: 1px solid #e2e8f0;
          border-radius: 12px;
          padding: 2rem;
          box-shadow: 0 1px 3px rgba(0, 0, 0, 0.02);
        }

        .cust-form-header {
          display: flex;
          align-items: flex-start;
          gap: 1rem;
          margin-bottom: 2rem;
          padding-bottom: 1.5rem;
          border-bottom: 1px solid #e2e8f0;
        }

        .cust-form-badge {
          width: 48px;
          height: 48px;
          border-radius: 10px;
          background: #eff6ff;
          display: flex;
          align-items: center;
          justify-content: center;
          flex-shrink: 0;
        }

        .cust-form-title {
          font-size: 1.5rem;
          font-weight: 700;
          color: #0f172a;
          margin: 0 0 0.375rem 0;
          letter-spacing: -0.02em;
        }

        .cust-form-desc {
          font-size: 0.875rem;
          color: #64748b;
          margin: 0;
          line-height: 1.4;
        }

        .cust-error-banner {
          display: flex;
          align-items: center;
          gap: 0.75rem;
          background: #fef2f2;
          border: 1px solid #fecaca;
          color: #991b1b;
          padding: 0.875rem 1rem;
          border-radius: 8px;
          font-size: 0.875rem;
          margin-bottom: 1.5rem;
        }

        .cust-form {
          display: flex;
          flex-direction: column;
          gap: 1.25rem;
        }

        .cust-form-grid {
          display: grid;
          grid-template-columns: repeat(2, 1fr);
          gap: 1.25rem;
        }

        @media (max-width: 640px) {
          .cust-form-grid {
            grid-template-columns: 1fr;
          }
        }

        .cust-form-group {
          display: flex;
          flex-direction: column;
          gap: 0.375rem;
        }

        .mt-3 { margin-top: 0.5rem; }

        .cust-label {
          font-size: 0.8125rem;
          font-weight: 600;
          color: #334155;
        }

        .text-required {
          color: #dc2626;
        }

        .cust-input, .cust-select, .cust-textarea {
          width: 100%;
          padding: 0.625rem 0.875rem;
          border: 1px solid #cbd5e1;
          border-radius: 6px;
          font-size: 0.875rem;
          color: #0f172a;
          background: #ffffff;
          transition: border-color 0.15s ease;
          box-sizing: border-box;
          font-family: inherit;
        }

        .cust-input:focus, .cust-select:focus, .cust-textarea:focus {
          outline: none;
          border-color: #2563eb;
          box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.1);
        }

        .cust-hint {
          font-size: 0.75rem;
          color: #94a3b8;
        }

        .cust-form-footer {
          margin-top: 1.5rem;
          padding-top: 1.5rem;
          border-top: 1px solid #e2e8f0;
          display: flex;
          align-items: center;
          justify-content: space-between;
          flex-wrap: wrap;
          gap: 1rem;
        }

        .cust-form-disclaimer {
          display: flex;
          align-items: center;
          gap: 0.5rem;
          font-size: 0.75rem;
          color: #059669;
          font-weight: 500;
        }

        .cust-form-actions {
          display: flex;
          align-items: center;
          gap: 0.75rem;
          margin-left: auto;
        }

        .cust-cancel-btn {
          padding: 0.625rem 1rem;
          border-radius: 6px;
          font-size: 0.875rem;
          font-weight: 500;
          color: #64748b;
          text-decoration: none;
        }

        .cust-cancel-btn:hover {
          color: #0f172a;
          background: #f1f5f9;
        }

        .cust-submit-btn {
          display: inline-flex;
          align-items: center;
          gap: 0.5rem;
          background: #2563eb;
          color: #ffffff;
          padding: 0.625rem 1.25rem;
          border-radius: 6px;
          font-size: 0.875rem;
          font-weight: 600;
          border: none;
          cursor: pointer;
          transition: background 0.15s ease;
        }

        .cust-submit-btn:hover:not(:disabled) {
          background: #1d4ed8;
        }

        .cust-submit-btn:disabled {
          opacity: 0.6;
          cursor: not-allowed;
        }

        .animate-spin {
          animation: spin 1s linear infinite;
        }

        @keyframes spin {
          0% { transform: rotate(0deg); }
          100% { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  );
}

export default CreateApplicationPage;
