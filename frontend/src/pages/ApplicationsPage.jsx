import React, { useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { Search, ArrowRight, RefreshCw, FileText, Database } from 'lucide-react';
import { api } from '../services/api';
import { RiskBadge, StatusBadge } from '../components/Common/Badges';
import { formatINR, formatDateTime } from '../services/formatters';
import { LoadingState } from '../components/Common/LoadingState';
import { ErrorAlert } from '../components/Common/ErrorAlert';
import { EmptyState } from '../components/Common/EmptyState';

export function ApplicationsPage() {
  const [applications, setApplications] = useState([]);
  const [loading, setLoading] = useState(true);
  const [loadingDemo, setLoadingDemo] = useState(false);
  const [error, setError] = useState(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [searchParams, setSearchParams] = useSearchParams();
  const navigate = useNavigate();

  const [viewScope, setViewScope] = useState('ALL'); // 'ALL' | 'CUSTOMER' | 'DEMO'

  const currentFilter = searchParams.get('filter') || 'ALL';
  const urlSearch = searchParams.get('search');

  useEffect(() => {
    if (urlSearch) {
      setSearchTerm(urlSearch);
      setViewScope('ALL');
    }
  }, [urlSearch]);

  const loadApplications = async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await api.getApplications();
      setApplications(res.applications || []);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadApplications();
    const handleSeeded = () => loadApplications();
    window.addEventListener('loan-data-seeded', handleSeeded);
    return () => window.removeEventListener('loan-data-seeded', handleSeeded);
  }, []);

  const handleLoadDemoData = async () => {
    try {
      setLoadingDemo(true);
      await api.seedDemoData();
      window.dispatchEvent(new CustomEvent('loan-data-seeded'));
      await loadApplications();
    } catch (err) {
      setError(err.message);
    } finally {
      setLoadingDemo(false);
    }
  };

  const handleFilterChange = (filterVal) => {
    if (filterVal === 'ALL') {
      searchParams.delete('filter');
    } else {
      searchParams.set('filter', filterVal);
    }
    setSearchParams(searchParams);
  };

  const getAppIssue = (app) => {
    if (app.primary_reason && app.primary_reason !== 'None' && app.primary_reason !== 'Standard Review') {
      return app.primary_reason;
    }
    const scenario = app.scenario;
    if (scenario === 'identity_mismatch') return 'Identity mismatch';
    if (scenario === 'missing_tax') return 'Missing tax return';
    if (scenario === 'missing_bank') return 'Missing bank statement';
    if (scenario === 'income_discrepancy') return 'Financial discrepancy';
    if (scenario === 'high_risk') return 'High credit risk';
    if (scenario === 'payslip_mismatch') return 'Payslip gross mismatch';
    if (scenario === 'multiple_issues') return 'Multiple issues';

    if (app.ml_risk_level === 'HIGH') return 'High credit risk';
    if (app.documents_count !== undefined && app.documents_count < 4) return 'Missing required documents';
    return app.primary_reason || 'None';
  };

  // Filter & search logic
  const filteredApps = applications.filter((app) => {
    const isDemo = /^A0(0[1-9]|10)$/.test(app.application_id);
    if (viewScope === 'DEMO' && !isDemo) return false;
    if (viewScope === 'CUSTOMER' && isDemo) return false;

    if (currentFilter === 'REQUIRED') {
      if (['APPROVED', 'REJECTED'].includes((app.status || '').toUpperCase())) return false;
      if (app.human_review_status !== 'REQUIRED' && app.human_review_required !== true && !['SUBMITTED', 'UNDER_REVIEW', 'ADDITIONAL_DOCUMENTS_REQUIRED'].includes(app.status)) return false;
    } else if (currentFilter === 'MISSING_DOCS') {
      const issue = getAppIssue(app).toLowerCase();
      const isReqDocs = (app.status || '').toUpperCase() === 'ADDITIONAL_DOCUMENTS_REQUIRED';
      if (!isReqDocs && !issue.includes('missing') && !issue.includes('document')) return false;
    } else if (currentFilter === 'COMPLETED') {
      const isDone = ['COMPLETED', 'OVERRIDDEN', 'APPROVED', 'REJECTED'].includes(app.human_review_status) || ['APPROVED', 'REJECTED'].includes((app.status || '').toUpperCase());
      if (!isDone) return false;
    }

    // Search query
    if (searchTerm.trim()) {
      const q = searchTerm.trim().toLowerCase();
      const matchId = app.application_id?.toLowerCase().includes(q);
      const matchNum = app.application_number?.toLowerCase().includes(q);
      const matchName = app.applicant_name?.toLowerCase().includes(q);
      const matchEmployer = app.employer?.toLowerCase().includes(q);
      const matchIssue = getAppIssue(app).toLowerCase().includes(q);
      return matchId || matchNum || matchName || matchEmployer || matchIssue;
    }

    return true;
  });

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
      {/* Page Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '1rem' }}>
        <div>
          <h1 style={{ fontSize: '1.5rem', fontWeight: 700, color: 'var(--color-text-primary)' }}>
            Applications
          </h1>
          <p style={{ fontSize: '0.85rem', color: 'var(--color-text-secondary)', marginTop: '0.2rem' }}>
            Underwriting pipeline ({filteredApps.length} of {applications.length} files)
          </p>
        </div>

        <button
          type="button"
          className="btn btn-secondary btn-sm"
          onClick={loadApplications}
          disabled={loading}
          style={{ display: 'inline-flex', alignItems: 'center', gap: '0.35rem' }}
        >
          <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
          <span>Refresh</span>
        </button>
      </div>

      {error && <ErrorAlert message={error} onRetry={loadApplications} />}

      {/* Scope Segmented Control (All vs Customer vs Demo) */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '0.75rem' }}>
        <div style={{ display: 'inline-flex', background: '#f1f5f9', padding: '3px', borderRadius: 'var(--radius-md)', border: '1px solid var(--color-border)' }}>
          <button
            type="button"
            className={`btn btn-sm ${viewScope === 'ALL' ? 'btn-primary' : ''}`}
            onClick={() => setViewScope('ALL')}
            style={{
              fontSize: '0.775rem',
              padding: '0.3rem 0.85rem',
              borderRadius: 'var(--radius-sm)',
              background: viewScope === 'ALL' ? 'var(--color-primary-700)' : 'transparent',
              color: viewScope === 'ALL' ? '#ffffff' : 'var(--color-text-secondary)',
              border: 'none',
              boxShadow: viewScope === 'ALL' ? '0 1px 2px rgba(0,0,0,0.1)' : 'none',
            }}
          >
            All Applications ({applications.length})
          </button>
          <button
            type="button"
            className={`btn btn-sm ${viewScope === 'CUSTOMER' ? 'btn-primary' : ''}`}
            onClick={() => setViewScope('CUSTOMER')}
            style={{
              fontSize: '0.775rem',
              padding: '0.3rem 0.85rem',
              borderRadius: 'var(--radius-sm)',
              background: viewScope === 'CUSTOMER' ? 'var(--color-primary-700)' : 'transparent',
              color: viewScope === 'CUSTOMER' ? '#ffffff' : 'var(--color-text-secondary)',
              border: 'none',
              boxShadow: viewScope === 'CUSTOMER' ? '0 1px 2px rgba(0,0,0,0.1)' : 'none',
            }}
          >
            Customer Applications
          </button>
          <button
            type="button"
            className={`btn btn-sm ${viewScope === 'DEMO' ? 'btn-primary' : ''}`}
            onClick={() => setViewScope('DEMO')}
            style={{
              fontSize: '0.775rem',
              padding: '0.3rem 0.85rem',
              borderRadius: 'var(--radius-sm)',
              background: viewScope === 'DEMO' ? 'var(--color-primary-700)' : 'transparent',
              color: viewScope === 'DEMO' ? '#ffffff' : 'var(--color-text-secondary)',
              border: 'none',
              boxShadow: viewScope === 'DEMO' ? '0 1px 2px rgba(0,0,0,0.1)' : 'none',
            }}
          >
            Demo Cases (A001–A010)
          </button>
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div className="card" style={{ padding: '0.875rem 1.25rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '1rem' }}>
          {/* Simple 4 Filters */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', flexWrap: 'wrap' }}>
            {[
              { id: 'ALL', label: 'All' },
              { id: 'REQUIRED', label: 'Needs Review' },
              { id: 'MISSING_DOCS', label: 'Missing Documents' },
              { id: 'COMPLETED', label: 'Completed' },
            ].map((f) => {
              const isActive = currentFilter === f.id;
              return (
                <button
                  key={f.id}
                  type="button"
                  className={`btn btn-sm ${isActive ? 'btn-primary' : 'btn-secondary'}`}
                  onClick={() => handleFilterChange(f.id)}
                  style={{ borderRadius: 'var(--radius-full)', padding: '0.25rem 0.85rem' }}
                >
                  {f.label}
                </button>
              );
            })}
          </div>

          {/* Search Box */}
          <div style={{ position: 'relative', width: '280px' }}>
            <Search
              size={14}
              style={{ position: 'absolute', left: '10px', top: '50%', transform: 'translateY(-50%)', color: 'var(--color-text-muted)' }}
            />
            <input
              type="text"
              className="form-input"
              placeholder="Search applications..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              style={{ paddingLeft: '32px', height: '34px', fontSize: '0.825rem' }}
            />
          </div>
        </div>
      </div>

      {/* Applications Data Table */}
      {loading ? (
        <LoadingState message="Loading loan applications..." />
      ) : filteredApps.length > 0 ? (
        <div className="table-wrapper">
          <table className="data-table">
            <thead>
              <tr>
                <th>Applicant</th>
                <th>Loan</th>
                <th>ML Risk</th>
                <th>Status</th>
                <th>Issue</th>
                <th>Updated</th>
                <th style={{ textAlign: 'right', width: '90px' }}>Action</th>
              </tr>
            </thead>
            <tbody>
              {filteredApps.map((app) => (
                <tr
                  key={app.application_id}
                  style={{ cursor: 'pointer' }}
                  onClick={() => navigate(`/applications/${app.application_id}`)}
                >
                  <td>
                    <div style={{ fontWeight: 600, color: 'var(--color-text-primary)' }}>
                      {app.applicant_name}
                    </div>
                    <div style={{ fontSize: '0.75rem', fontFamily: 'var(--font-mono)', color: 'var(--color-primary-700)' }}>
                      {app.application_number || app.application_id}
                    </div>
                  </td>
                  <td style={{ fontWeight: 600 }}>
                    {formatINR(app.loan_amount)}
                  </td>
                  <td>
                    <RiskBadge level={app.ml_risk_level} score={app.ml_risk_score} />
                  </td>
                  <td>
                    <StatusBadge
                      status={
                        ['APPROVED', 'REJECTED', 'ESCALATED', 'ADDITIONAL_DOCUMENTS_REQUIRED'].includes((app.status || '').toUpperCase())
                          ? app.status
                          : (app.human_review_status || app.status || 'REQUIRED')
                      }
                    />
                  </td>
                  <td style={{ fontSize: '0.85rem', color: 'var(--color-text-secondary)' }}>
                    {getAppIssue(app)}
                  </td>
                  <td style={{ fontSize: '0.8rem', color: 'var(--color-text-muted)', whiteSpace: 'nowrap' }}>
                    {app.created_at ? formatDateTime(app.created_at) : 'Today'}
                  </td>
                  <td style={{ textAlign: 'right' }}>
                    <button
                      type="button"
                      className="btn btn-secondary btn-sm"
                      onClick={(e) => {
                        e.stopPropagation();
                        navigate(`/applications/${app.application_id}`);
                      }}
                    >
                      <span>Open</span>
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <EmptyState
          title={applications.length === 0 ? "No Applications Loaded" : "No applications match this view"}
          description={
            applications.length === 0
              ? "The loan processing database is currently empty. Click below to load and process all 10 demo applications."
              : (searchTerm ? `No loan applications found matching "${searchTerm}".` : 'Try selecting a different filter.')
          }
          icon={FileText}
          action={
            applications.length === 0 ? (
              <button
                type="button"
                className="btn btn-primary"
                onClick={handleLoadDemoData}
                disabled={loadingDemo}
                style={{ display: 'inline-flex', alignItems: 'center', gap: '0.4rem' }}
              >
                <Database size={15} />
                <span>{loadingDemo ? 'Loading Demo Data...' : 'Load Demo Data'}</span>
              </button>
            ) : (
              <button
                type="button"
                className="btn btn-secondary btn-sm"
                onClick={() => {
                  setSearchTerm('');
                  handleFilterChange('ALL');
                }}
              >
                Clear Filters
              </button>
            )
          }
        />
      )}
    </div>
  );
}

