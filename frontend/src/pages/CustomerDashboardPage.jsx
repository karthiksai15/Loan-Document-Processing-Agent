import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import {
  FileText,
  PlusCircle,
  Clock,
  CheckCircle2,
  AlertCircle,
  ChevronRight,
  UploadCloud,
  FileCheck2,
} from 'lucide-react';
import { api } from '../services/api';
import { LoadingState } from '../components/Common/LoadingState';

export function formatCurrency(amount) {
  if (amount === null || amount === undefined || isNaN(amount)) return '₹0';
  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    maximumFractionDigits: 0,
  }).format(amount);
}

export function getStatusBadge(status) {
  const norm = (status || '').toUpperCase();
  switch (norm) {
    case 'APPROVED':
      return { label: 'Approved', colorClass: 'badge-approved', icon: CheckCircle2 };
    case 'REJECTED':
      return { label: 'Rejected', colorClass: 'badge-rejected', icon: AlertCircle };
    case 'ESCALATED':
      return { label: 'Escalated', colorClass: 'badge-rejected', icon: AlertCircle };
    case 'ADDITIONAL_DOCUMENTS_REQUIRED':
      return { label: 'Documents Requested', colorClass: 'badge-in-review', icon: AlertCircle };
    case 'UNDER_REVIEW':
      return { label: 'Under Review', colorClass: 'badge-in-review', icon: Clock };
    case 'IN_REVIEW':
      return { label: 'In Review', colorClass: 'badge-in-review', icon: Clock };
    case 'SUBMITTED':
      return { label: 'Submitted', colorClass: 'badge-submitted', icon: Clock };
    case 'DRAFT':
    default:
      return { label: 'Draft', colorClass: 'badge-draft', icon: UploadCloud };
  }
}

export function CustomerDashboardPage() {
  const [applications, setApplications] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchApplications = async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await api.getCustomerApplications();
      setApplications(res?.applications || []);
    } catch (err) {
      setError(err?.message || 'Failed to load your loan applications.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchApplications();
  }, []);

  if (loading) {
    return <LoadingState message="Loading your loan applications..." />;
  }

  const draftsCount = applications.filter((a) => (a.status || '').toUpperCase() === 'DRAFT').length;
  const submittedCount = applications.filter((a) => ['SUBMITTED', 'IN_REVIEW', 'UNDER_REVIEW', 'ADDITIONAL_DOCUMENTS_REQUIRED'].includes((a.status || '').toUpperCase())).length;
  const approvedCount = applications.filter((a) => (a.status || '').toUpperCase() === 'APPROVED').length;
  const docsRequiredList = applications.filter((a) => (a.status || '').toUpperCase() === 'ADDITIONAL_DOCUMENTS_REQUIRED');

  return (
    <div className="customer-dashboard">
      {/* Header section */}
      <div className="cust-dash-header">
        <div>
          <h1 className="cust-dash-title">My Loan Applications</h1>
          <p className="cust-dash-subtitle">
            Manage your loan requests, upload supporting documents, and track underwriting decisions in real time.
          </p>
        </div>
        <Link to="/customer/applications/new" className="cust-primary-btn">
          <PlusCircle size={18} />
          <span>New Application</span>
        </Link>
      </div>

      {error && (
        <div className="cust-error-banner">
          <AlertCircle size={18} />
          <span>{error}</span>
          <button type="button" onClick={fetchApplications} className="cust-retry-btn">
            Retry
          </button>
        </div>
      )}

      {docsRequiredList.length > 0 && (
        <div style={{ background: '#fffbeb', border: '1px solid #fde68a', borderRadius: '10px', padding: '1rem 1.25rem', marginBottom: '1.25rem', display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '1rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            <AlertCircle size={22} color="#d97706" style={{ flexShrink: 0 }} />
            <div>
              <div style={{ fontWeight: 700, color: '#92400e', fontSize: '0.925rem' }}>
                Action Required: Additional Documents Requested
              </div>
              <div style={{ fontSize: '0.825rem', color: '#b45309', marginTop: '2px' }}>
                Our credit officer requested additional documentation on application <strong>{docsRequiredList[0].application_number || docsRequiredList[0].application_id}</strong>.
              </div>
            </div>
          </div>
          <Link
            to={`/customer/applications/${docsRequiredList[0].application_number || docsRequiredList[0].application_id}`}
            className="cust-primary-btn"
            style={{ fontSize: '0.825rem', padding: '0.45rem 1rem', textDecoration: 'none' }}
          >
            Upload Documents Now
          </Link>
        </div>
      )}

      {/* Stats summary cards */}
      <div className="cust-stats-grid">
        <div className="cust-stat-card">
          <div className="stat-icon-wrap stat-total">
            <FileText size={20} color="#2563eb" />
          </div>
          <div>
            <span className="stat-number">{applications.length}</span>
            <span className="stat-label">Total Applications</span>
          </div>
        </div>

        <div className="cust-stat-card">
          <div className="stat-icon-wrap stat-draft">
            <UploadCloud size={20} color="#f59e0b" />
          </div>
          <div>
            <span className="stat-number">{draftsCount}</span>
            <span className="stat-label">Action Required (Drafts)</span>
          </div>
        </div>

        <div className="cust-stat-card">
          <div className="stat-icon-wrap stat-review">
            <Clock size={20} color="#8b5cf6" />
          </div>
          <div>
            <span className="stat-number">{submittedCount}</span>
            <span className="stat-label">Underwriting In Review</span>
          </div>
        </div>

        <div className="cust-stat-card">
          <div className="stat-icon-wrap stat-approved">
            <FileCheck2 size={20} color="#10b981" />
          </div>
          <div>
            <span className="stat-number">{approvedCount}</span>
            <span className="stat-label">Approved Loans</span>
          </div>
        </div>
      </div>

      {/* Applications list */}
      <div className="cust-apps-section">
        <h2 className="cust-section-title">Application Records</h2>

        {applications.length === 0 ? (
          <div className="cust-empty-state">
            <div className="cust-empty-icon">
              <FileText size={36} color="#94a3b8" />
            </div>
            <h3 className="cust-empty-title">No loan applications yet</h3>
            <p className="cust-empty-desc">
              Start your loan journey with GenBank. Submit your financial profile and upload required documents in simple guided steps.
            </p>
            <Link to="/customer/applications/new" className="cust-primary-btn">
              <PlusCircle size={18} />
              <span>Start Application Now</span>
            </Link>
          </div>
        ) : (
          <div className="cust-table-card">
            <table className="cust-table">
              <thead>
                <tr>
                  <th>Application No</th>
                  <th>Applicant Name</th>
                  <th>Loan Amount</th>
                  <th>Documents</th>
                  <th>Status</th>
                  <th>Created</th>
                  <th className="text-right">Action</th>
                </tr>
              </thead>
              <tbody>
                {applications.map((app) => {
                  const badge = getStatusBadge(app.status);
                  const Icon = badge.icon;
                  const docCount = app.documents_count || (app.documents?.length || 0);

                  return (
                    <tr key={app.application_id}>
                      <td className="font-mono font-semibold text-primary">
                        {app.application_number || app.application_id}
                      </td>
                      <td>{app.applicant_name}</td>
                      <td className="font-semibold text-slate-800">
                        {formatCurrency(app.loan_amount)}
                      </td>
                      <td>
                        <span className="cust-doc-counter">
                          <UploadCloud size={14} />
                          {docCount} {docCount === 1 ? 'file' : 'files'}
                        </span>
                      </td>
                      <td>
                        <span className={`cust-status-badge ${badge.colorClass}`}>
                          <Icon size={12} />
                          {badge.label}
                        </span>
                      </td>
                      <td className="text-muted text-sm">
                        {app.created_at ? new Date(app.created_at).toLocaleDateString() : '—'}
                      </td>
                      <td className="text-right">
                        <Link
                          to={`/customer/applications/${app.application_id}`}
                          className="cust-table-action-btn"
                        >
                          <span>{app.status === 'DRAFT' ? 'Upload & Submit' : 'View Details'}</span>
                          <ChevronRight size={14} />
                        </Link>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      <style>{`
        .customer-dashboard {
          display: flex;
          flex-direction: column;
          gap: 2rem;
        }

        .cust-dash-header {
          display: flex;
          align-items: center;
          justify-content: space-between;
          flex-wrap: wrap;
          gap: 1rem;
        }

        .cust-dash-title {
          font-size: 1.75rem;
          font-weight: 700;
          color: #0f172a;
          margin: 0 0 0.375rem 0;
          letter-spacing: -0.02em;
        }

        .cust-dash-subtitle {
          font-size: 0.875rem;
          color: #64748b;
          margin: 0;
          max-width: 650px;
          line-height: 1.5;
        }

        .cust-primary-btn {
          display: inline-flex;
          align-items: center;
          gap: 0.5rem;
          background: #2563eb;
          color: #ffffff;
          padding: 0.625rem 1.25rem;
          border-radius: 8px;
          font-size: 0.875rem;
          font-weight: 600;
          text-decoration: none;
          border: none;
          cursor: pointer;
          transition: all 0.15s ease;
          box-shadow: 0 2px 4px rgba(37, 99, 235, 0.2);
        }

        .cust-primary-btn:hover {
          background: #1d4ed8;
          box-shadow: 0 4px 6px rgba(37, 99, 235, 0.25);
        }

        .cust-error-banner {
          display: flex;
          align-items: center;
          gap: 0.75rem;
          background: #fef2f2;
          border: 1px solid #fecaca;
          color: #991b1b;
          padding: 0.875rem 1.25rem;
          border-radius: 8px;
          font-size: 0.875rem;
        }

        .cust-retry-btn {
          margin-left: auto;
          background: #fee2e2;
          border: 1px solid #fca5a5;
          color: #991b1b;
          padding: 0.25rem 0.625rem;
          border-radius: 4px;
          font-size: 0.75rem;
          font-weight: 600;
          cursor: pointer;
        }

        .cust-stats-grid {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
          gap: 1rem;
        }

        .cust-stat-card {
          background: #ffffff;
          border: 1px solid #e2e8f0;
          border-radius: 10px;
          padding: 1.25rem;
          display: flex;
          align-items: center;
          gap: 1rem;
          box-shadow: 0 1px 3px rgba(0, 0, 0, 0.02);
        }

        .stat-icon-wrap {
          width: 44px;
          height: 44px;
          border-radius: 10px;
          display: flex;
          align-items: center;
          justify-content: center;
        }

        .stat-total { background: #eff6ff; }
        .stat-draft { background: #fffbeb; }
        .stat-review { background: #f5f3ff; }
        .stat-approved { background: #ecfdf5; }

        .stat-number {
          display: block;
          font-size: 1.5rem;
          font-weight: 700;
          color: #0f172a;
          line-height: 1.2;
        }

        .stat-label {
          display: block;
          font-size: 0.75rem;
          font-weight: 500;
          color: #64748b;
          margin-top: 0.125rem;
        }

        .cust-apps-section {
          display: flex;
          flex-direction: column;
          gap: 1rem;
        }

        .cust-section-title {
          font-size: 1.125rem;
          font-weight: 700;
          color: #0f172a;
          margin: 0;
        }

        .cust-empty-state {
          background: #ffffff;
          border: 1px dashed #cbd5e1;
          border-radius: 12px;
          padding: 3.5rem 2rem;
          text-align: center;
          display: flex;
          flex-direction: column;
          align-items: center;
          gap: 1rem;
        }

        .cust-empty-icon {
          width: 64px;
          height: 64px;
          border-radius: 50%;
          background: #f1f5f9;
          display: flex;
          align-items: center;
          justify-content: center;
        }

        .cust-empty-title {
          font-size: 1.125rem;
          font-weight: 600;
          color: #0f172a;
          margin: 0;
        }

        .cust-empty-desc {
          font-size: 0.875rem;
          color: #64748b;
          max-width: 480px;
          line-height: 1.5;
          margin: 0;
        }

        .cust-table-card {
          background: #ffffff;
          border: 1px solid #e2e8f0;
          border-radius: 10px;
          overflow-x: auto;
          box-shadow: 0 1px 3px rgba(0, 0, 0, 0.02);
        }

        .cust-table {
          width: 100%;
          border-collapse: collapse;
          font-size: 0.875rem;
          text-align: left;
        }

        .cust-table th {
          background: #f8fafc;
          padding: 0.875rem 1rem;
          font-weight: 600;
          color: #475569;
          border-bottom: 1px solid #e2e8f0;
          white-space: nowrap;
        }

        .cust-table td {
          padding: 1rem;
          border-bottom: 1px solid #f1f5f9;
          vertical-align: middle;
        }

        .cust-table tr:last-child td {
          border-bottom: none;
        }

        .cust-table tr:hover {
          background: #f8fafc;
        }

        .text-right { text-align: right; }
        .text-muted { color: #64748b; }
        .text-sm { font-size: 0.8125rem; }
        .font-mono { font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace; }
        .font-semibold { font-weight: 600; }
        .text-primary { color: #2563eb; }

        .cust-doc-counter {
          display: inline-flex;
          align-items: center;
          gap: 0.375rem;
          padding: 0.25rem 0.625rem;
          background: #f1f5f9;
          border-radius: 12px;
          font-size: 0.75rem;
          font-weight: 500;
          color: #475569;
        }

        .cust-status-badge {
          display: inline-flex;
          align-items: center;
          gap: 0.375rem;
          padding: 0.25rem 0.625rem;
          border-radius: 12px;
          font-size: 0.75rem;
          font-weight: 600;
        }

        .badge-draft { background: #fef3c7; color: #b45309; }
        .badge-submitted { background: #e0e7ff; color: #3730a3; }
        .badge-in-review { background: #f3e8ff; color: #6b21a8; }
        .badge-approved { background: #d1fae5; color: #065f46; }
        .badge-rejected { background: #fee2e2; color: #991b1b; }

        .cust-table-action-btn {
          display: inline-flex;
          align-items: center;
          gap: 0.25rem;
          color: #2563eb;
          font-weight: 600;
          font-size: 0.8125rem;
          text-decoration: none;
          padding: 0.375rem 0.625rem;
          border-radius: 6px;
          transition: background 0.15s ease;
        }

        .cust-table-action-btn:hover {
          background: #eff6ff;
        }
      `}</style>
    </div>
  );
}

export default CustomerDashboardPage;
