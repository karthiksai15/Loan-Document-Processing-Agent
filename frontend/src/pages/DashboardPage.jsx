import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  FileText,
  AlertTriangle,
  Flame,
  FileQuestion,
  ArrowRight,
  RefreshCw,
  ExternalLink,
  Database,
} from 'lucide-react';
import { api } from '../services/api';
import { MetricCard } from '../components/Common/MetricCard';
import { RiskBadge, StatusBadge } from '../components/Common/Badges';
import { formatINR, formatPercent } from '../services/formatters';
import { LoadingState } from '../components/Common/LoadingState';
import { ErrorAlert } from '../components/Common/ErrorAlert';

export function DashboardPage() {
  const [overview, setOverview] = useState(null);
  const [loading, setLoading] = useState(true);
  const [loadingDemo, setLoadingDemo] = useState(false);
  const [error, setError] = useState(null);
  const navigate = useNavigate();

  const loadDashboard = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await api.getDashboardOverview();
      setOverview(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleLoadDemoData = async () => {
    try {
      setLoadingDemo(true);
      await api.seedDemoData();
      window.dispatchEvent(new CustomEvent('loan-data-seeded'));
      await loadDashboard();
    } catch (err) {
      setError(err.message);
    } finally {
      setLoadingDemo(false);
    }
  };

  useEffect(() => {
    loadDashboard();
    const handleSeeded = () => loadDashboard();
    window.addEventListener('loan-data-seeded', handleSeeded);
    return () => window.removeEventListener('loan-data-seeded', handleSeeded);
  }, []);

  if (loading) return <LoadingState message="Loading loan officer workspace..." />;

  const attentionQueue = overview?.attention_queue || [];

  const getPrimaryIssueLabel = (item) => {
    if (item.primary_issue && item.primary_issue !== 'Standard Review' && item.primary_issue !== 'None') {
      return item.primary_issue;
    }
    const scenario = item.scenario;
    if (scenario === 'identity_mismatch') return 'Identity mismatch';
    if (scenario === 'missing_tax') return 'Missing tax return';
    if (scenario === 'missing_bank') return 'Missing bank statement';
    if (scenario === 'income_discrepancy') return 'Financial discrepancy';
    if (scenario === 'high_risk') return 'High credit risk';
    if (scenario === 'payslip_mismatch') return 'Payslip gross mismatch';
    if (scenario === 'multiple_issues') return 'Multiple issues';

    if (item.primary_reason && item.primary_reason !== 'Standard Review' && item.primary_reason !== 'None') {
      return item.primary_reason;
    }
    if (item.ml_risk_level === 'HIGH') return 'High credit risk';
    return item.primary_issue || 'Standard Review';
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
      {/* Page Title & Refresh */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '1rem' }}>
        <div>
          <h1 style={{ fontSize: '1.5rem', fontWeight: 700, color: 'var(--color-text-primary)' }}>
            Loan Officer Dashboard
          </h1>
          <p style={{ fontSize: '0.85rem', color: 'var(--color-text-secondary)', marginTop: '0.2rem' }}>
            What applications need your attention today
          </p>
        </div>

        <button
          type="button"
          className="btn btn-secondary btn-sm"
          onClick={loadDashboard}
          style={{ display: 'inline-flex', alignItems: 'center', gap: '0.35rem' }}
        >
          <RefreshCw size={14} />
          <span>Refresh</span>
        </button>
      </div>

      {error && <ErrorAlert message={error} onRetry={loadDashboard} />}

      {/* Top 4 Metrics Row */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '1rem' }}>
        <MetricCard
          title="Total Applications"
          value={overview?.total_applications || 0}
          subtitle="Processed in pipeline"
          icon={FileText}
          onClick={() => navigate('/applications')}
        />
        <MetricCard
          title="Needs Review"
          value={overview?.review_required_count || 0}
          subtitle="Requires officer action"
          icon={AlertTriangle}
          highlight="danger"
          onClick={() => navigate('/applications?filter=REQUIRED')}
        />
        <MetricCard
          title="High Priority"
          value={overview?.high_priority_count || 0}
          subtitle="Urgent attention"
          icon={Flame}
          highlight="warning"
          onClick={() => navigate('/applications?filter=HIGH_PRIORITY')}
        />
        <MetricCard
          title="Documents Missing"
          value={overview?.documents_pending_count || 0}
          subtitle="Pending follow-up"
          icon={FileQuestion}
          highlight="warning"
          onClick={() => navigate('/applications?filter=DOCS_PENDING')}
        />
      </div>

      {/* Main Section: NEEDS YOUR ATTENTION */}
      <div className="card" style={{ padding: '0', overflow: 'hidden' }}>
        <div style={{ padding: '1.25rem 1.5rem', borderBottom: '1px solid var(--color-border)', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <div>
            <h2 style={{ fontSize: '1.1rem', fontWeight: 700, color: 'var(--color-text-primary)' }}>
              NEEDS YOUR ATTENTION
            </h2>
            <span style={{ fontSize: '0.8rem', color: 'var(--color-text-secondary)' }}>
              Applications requiring immediate verification, document follow-up, or officer decision
            </span>
          </div>
          <button
            type="button"
            className="btn btn-secondary btn-sm"
            onClick={() => navigate('/applications')}
          >
            <span>View All</span>
            <ArrowRight size={14} />
          </button>
        </div>

        <div className="table-wrapper" style={{ border: 'none', borderRadius: 0, margin: 0 }}>
          <table className="data-table">
            <thead>
              <tr>
                <th style={{ width: '100px' }}>Loan ID</th>
                <th>Applicant</th>
                <th>Loan Amount</th>
                <th>ML Risk</th>
                <th>Status</th>
                <th>Main Issue</th>
                <th style={{ textAlign: 'right', width: '100px' }}>Action</th>
              </tr>
            </thead>
            <tbody>
              {attentionQueue.length > 0 ? (
                attentionQueue.map((item) => (
                  <tr
                    key={item.application_id}
                    style={{ cursor: 'pointer' }}
                    onClick={() => navigate(`/applications/${item.application_id}`)}
                  >
                    <td style={{ fontFamily: 'var(--font-mono)', fontWeight: 600, color: 'var(--color-primary-700)' }}>
                      {item.application_id}
                    </td>
                    <td style={{ fontWeight: 600, color: 'var(--color-text-primary)' }}>
                      {item.applicant_name}
                    </td>
                    <td style={{ fontWeight: 600 }}>
                      {formatINR(item.loan_amount)}
                    </td>
                    <td>
                      <RiskBadge level={item.ml_risk_level} score={item.ml_risk_score} />
                    </td>
                    <td>
                      <StatusBadge status={item.human_review_status || 'REQUIRED'} />
                    </td>
                    <td style={{ fontSize: '0.85rem', color: 'var(--color-text-secondary)' }}>
                      {getPrimaryIssueLabel(item)}
                    </td>
                    <td style={{ textAlign: 'right' }}>
                      <button
                        type="button"
                        className="btn btn-primary btn-sm"
                        onClick={(e) => {
                          e.stopPropagation();
                          navigate(`/applications/${item.application_id}`);
                        }}
                      >
                        <span>Open</span>
                      </button>
                    </td>
                  </tr>
                ))
              ) : overview?.total_applications === 0 ? (
                <tr>
                  <td colSpan={7} style={{ textAlign: 'center', padding: '3.5rem 1.5rem', color: 'var(--color-text-muted)' }}>
                    <Database size={32} color="var(--color-primary-600)" style={{ margin: '0 auto 0.75rem' }} />
                    <div style={{ fontSize: '1.05rem', fontWeight: 700, color: 'var(--color-text-primary)', marginBottom: '0.35rem' }}>
                      No Loan Applications Loaded
                    </div>
                    <p style={{ fontSize: '0.825rem', color: 'var(--color-text-secondary)', maxWidth: '440px', margin: '0 auto 1.25rem' }}>
                      The workspace is currently empty. Click below to load and analyze all 10 demo applications.
                    </p>
                    <button
                      type="button"
                      className="btn btn-primary"
                      onClick={handleLoadDemoData}
                      disabled={loadingDemo}
                      style={{ display: 'inline-flex', alignItems: 'center', gap: '0.4rem', margin: '0 auto' }}
                    >
                      <Database size={14} />
                      <span>{loadingDemo ? 'Loading Demo Data...' : 'Load Demo Data'}</span>
                    </button>
                  </td>
                </tr>
              ) : (
                <tr>
                  <td colSpan={7} style={{ textAlign: 'center', padding: '2.5rem', color: 'var(--color-text-muted)' }}>
                    No applications currently require urgent attention.
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

