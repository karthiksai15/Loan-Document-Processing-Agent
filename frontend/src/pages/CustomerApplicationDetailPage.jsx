import React, { useState, useEffect, useRef } from 'react';
import { useParams, Link } from 'react-router-dom';
import {
  ArrowLeft,
  UploadCloud,
  FileCheck2,
  Trash2,
  AlertCircle,
  Clock,
  CheckCircle2,
  Loader2,
  FileText,
  ShieldCheck,
  Send,
} from 'lucide-react';
import { api } from '../services/api';
import { LoadingState } from '../components/Common/LoadingState';
import { formatCurrency, getStatusBadge } from './CustomerDashboardPage';

const REQUIRED_DOC_TYPES = [
  {
    type: 'PAYSLIP',
    label: 'Salary Slip / Payslip',
    description: 'Recent 3 months salary slip showing employer, earnings, and deductions.',
  },
  {
    type: 'BANK_STATEMENT',
    label: 'Bank Account Statement',
    description: 'Last 6 months bank statement showing regular salary deposits.',
  },
  {
    type: 'KYC',
    label: 'Identity Proof (KYC)',
    description: 'Government issued identity document (PAN Card, Aadhaar, or Passport).',
  },
  {
    type: 'TAX_RETURN',
    label: 'Income Tax Return / Form 16',
    description: 'Latest ITR-V acknowledgement or Form 16 for income verification.',
  },
];

export function CustomerApplicationDetailPage() {
  const { applicationId } = useParams();
  const [application, setApplication] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Per-slot upload state
  const [uploadingSlot, setUploadingSlot] = useState(null);
  const [submittingApp, setSubmittingApp] = useState(false);
  const [actionSuccess, setActionSuccess] = useState(null);

  const fileInputRefs = useRef({});

  const fetchApplicationDetails = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await api.getCustomerApplication(applicationId);
      setApplication(data);
    } catch (err) {
      setError(err?.message || 'Failed to load application details.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchApplicationDetails();
  }, [applicationId]);

  const handleFileUpload = async (documentType, file) => {
    if (!file) return;

    setUploadingSlot(documentType);
    setError(null);
    setActionSuccess(null);

    try {
      await api.uploadCustomerDocument(applicationId, file, documentType);
      const isReq = (application?.status || '').toUpperCase() === 'ADDITIONAL_DOCUMENTS_REQUIRED';
      setActionSuccess(
        isReq
          ? `Successfully uploaded ${file.name}! Application has resumed underwriting review.`
          : `Successfully uploaded ${file.name}`
      );
      await fetchApplicationDetails();
    } catch (err) {
      setError(err?.message || `Failed to upload document for ${documentType}.`);
    } finally {
      setUploadingSlot(null);
      if (fileInputRefs.current[documentType]) {
        fileInputRefs.current[documentType].value = '';
      }
    }
  };

  const handleDeleteDocument = async (docId, docLabel) => {
    if (!window.confirm(`Are you sure you want to remove this ${docLabel}?`)) {
      return;
    }

    setError(null);
    setActionSuccess(null);

    try {
      await api.deleteCustomerDocument(applicationId, docId);
      setActionSuccess('Document removed successfully.');
      await fetchApplicationDetails();
    } catch (err) {
      setError(err?.message || 'Failed to remove document.');
    }
  };

  const handleSubmitApplication = async () => {
    if (
      !window.confirm(
        'Submit this application for underwriting review? You will not be able to modify uploaded documents once submitted.'
      )
    ) {
      return;
    }

    setSubmittingApp(true);
    setError(null);
    setActionSuccess(null);

    try {
      const res = await api.submitCustomerApplication(applicationId);
      setActionSuccess(res?.message || 'Application submitted successfully!');
      await fetchApplicationDetails();
    } catch (err) {
      setError(err?.message || 'Failed to submit application.');
    } finally {
      setSubmittingApp(false);
    }
  };

  if (loading) {
    return <LoadingState message="Retrieving application documentation..." />;
  }

  if (!application) {
    return (
      <div className="cust-error-page">
        <AlertCircle size={32} color="#dc2626" />
        <h2>Application Not Found</h2>
        <p>The requested loan application could not be found or you do not have permission to view it.</p>
        <Link to="/customer/dashboard" className="cust-primary-btn">
          Back to Dashboard
        </Link>
      </div>
    );
  }

  const statusUpper = (application.status || '').toUpperCase();
  const isDraft = statusUpper === 'DRAFT';
  const isDocsRequired = statusUpper === 'ADDITIONAL_DOCUMENTS_REQUIRED';
  const isApproved = statusUpper === 'APPROVED';
  const isRejected = statusUpper === 'REJECTED';
  const isEscalated = statusUpper === 'ESCALATED';
  const canUpload = isDraft || isDocsRequired;
  const badge = getStatusBadge(application.status);
  const StatusIcon = badge.icon;
  const docsList = application.documents || [];

  return (
    <div className="cust-detail-container">
      {/* Navigation & Header */}
      <div className="cust-detail-header-nav">
        <Link to="/customer/dashboard" className="cust-back-link">
          <ArrowLeft size={16} />
          <span>Back to My Applications</span>
        </Link>
      </div>

      {/* Main Status Header Card */}
      <div className="cust-detail-hero">
        <div className="cust-hero-main">
          <div className="cust-hero-appnum">
            <span className="cust-app-id-tag">Application Reference</span>
            <h1 className="cust-app-number">
              {application.application_number || application.application_id}
            </h1>
          </div>
          <div className="cust-hero-status">
            <span className={`cust-status-badge ${badge.colorClass}`}>
              <StatusIcon size={14} />
              {badge.label}
            </span>
          </div>
        </div>

        <div className="cust-hero-grid">
          <div className="cust-hero-item">
            <span className="hero-label">Applicant Name</span>
            <span className="hero-val">{application.applicant_name}</span>
          </div>
          <div className="cust-hero-item">
            <span className="hero-label">Loan Amount</span>
            <span className="hero-val font-semibold">
              {formatCurrency(application.loan_amount)}
            </span>
          </div>
          <div className="cust-hero-item">
            <span className="hero-label">Gross Income</span>
            <span className="hero-val">
              {application.income_annum ? formatCurrency(application.income_annum) : '—'}
            </span>
          </div>
          <div className="cust-hero-item">
            <span className="hero-label">Tenure</span>
            <span className="hero-val">
              {application.loan_term ? `${application.loan_term} Months` : '—'}
            </span>
          </div>
        </div>
      </div>

      {/* Notifications / Feedback */}
      {error && (
        <div className="cust-error-banner" role="alert">
          <AlertCircle size={18} className="flex-shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {actionSuccess && (
        <div className="cust-success-banner" role="status">
          <CheckCircle2 size={18} className="flex-shrink-0" />
          <span>{actionSuccess}</span>
        </div>
      )}

      {/* Application Lifecycle Stepper */}
      <div className="cust-stepper-card">
        <h2 className="cust-card-title">Application Status Progression</h2>
        <div className="cust-stepper">
          {/* Step 1: Created */}
          <div className="stepper-step completed">
            <div className="step-indicator">
              <CheckCircle2 size={18} />
            </div>
            <div className="step-content">
              <span className="step-title">1. Application Created</span>
              <span className="step-desc">Application reference generated</span>
            </div>
          </div>

          <div className={`stepper-line ${docsList.length > 0 ? 'completed' : ''}`} />

          {/* Step 2: Documents */}
          <div
            className={`stepper-step ${
              docsList.length > 0 ? 'completed' : isDraft ? 'active' : ''
            }`}
          >
            <div className="step-indicator">
              {docsList.length > 0 ? <CheckCircle2 size={18} /> : 2}
            </div>
            <div className="step-content">
              <span className="step-title">2. Upload Documents</span>
              <span className="step-desc">{docsList.length} files attached</span>
            </div>
          </div>

          <div className={`stepper-line ${!isDraft ? 'completed' : ''}`} />

          {/* Step 3: Submission & Review */}
          <div
            className={`stepper-step ${
              !isDraft ? (isApproved ? 'completed' : 'active') : ''
            }`}
          >
            <div className="step-indicator">
              {isApproved ? (
                <CheckCircle2 size={18} />
              ) : !isDraft ? (
                <Clock size={16} />
              ) : (
                3
              )}
            </div>
            <div className="step-content">
              <span className="step-title">3. Underwriting Review</span>
              <span className="step-desc">
                {isDraft
                  ? 'Awaiting submission'
                  : isApproved
                  ? 'Underwriting completed'
                  : isDocsRequired
                  ? 'Documents requested'
                  : 'AI & Officer in review'}
              </span>
            </div>
          </div>

          <div
            className={`stepper-line ${
              isApproved || isRejected || isEscalated ? 'completed' : ''
            }`}
          />

          {/* Step 4: Decision */}
          <div
            className={`stepper-step ${
              isApproved || isRejected || isEscalated ? 'completed' : ''
            }`}
          >
            <div className="step-indicator">
              {isApproved ? (
                <CheckCircle2 size={18} />
              ) : isRejected || isEscalated ? (
                <AlertCircle size={18} />
              ) : (
                4
              )}
            </div>
            <div className="step-content">
              <span className="step-title">4. Decision</span>
              <span className="step-desc">
                {isApproved
                  ? 'Approved'
                  : isRejected
                  ? 'Declined'
                  : isEscalated
                  ? 'Escalated'
                  : 'Pending final review'}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Action Required: Requested Documents */}
      {isDocsRequired && (
        <div style={{ background: '#fffbeb', border: '1px solid #fde68a', borderRadius: '12px', padding: '1.25rem 1.5rem', marginBottom: '1.5rem' }}>
          <div style={{ display: 'flex', alignItems: 'flex-start', gap: '0.85rem' }}>
            <AlertCircle size={24} color="#d97706" style={{ flexShrink: 0, marginTop: '2px' }} />
            <div style={{ flex: 1 }}>
              <h3 style={{ fontSize: '1.05rem', fontWeight: 700, color: '#92400e', marginBottom: '0.35rem' }}>
                Action Required: Additional Documentation Requested
              </h3>
              <p style={{ fontSize: '0.85rem', color: '#b45309', marginBottom: '0.75rem' }}>
                Our credit officer has requested clarification or missing documents. Please upload the requested file(s) below. Once uploaded, your file will immediately re-enter automated review.
              </p>
              {application.requested_documents && application.requested_documents.length > 0 && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                  {application.requested_documents.map((req, idx) => (
                    <div key={idx} style={{ background: '#ffffff', border: '1px solid #fcd34d', borderRadius: '8px', padding: '0.75rem 1rem' }}>
                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                        <span style={{ fontWeight: 700, color: '#92400e', fontSize: '0.875rem' }}>{req.doc_type}</span>
                        {req.requested_by && <span style={{ fontSize: '0.75rem', color: '#78350f' }}>Requested by: {req.requested_by}</span>}
                      </div>
                      <p style={{ fontSize: '0.825rem', color: '#451a03', marginTop: '0.25rem' }}>{req.reason}</p>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Decision: Approved */}
      {isApproved && (
        <div style={{ background: '#f0fdf4', border: '1px solid #86efac', borderRadius: '12px', padding: '1.25rem 1.5rem', marginBottom: '1.5rem', display: 'flex', alignItems: 'center', gap: '1rem' }}>
          <CheckCircle2 size={32} color="#16a34a" style={{ flexShrink: 0 }} />
          <div>
            <h3 style={{ fontSize: '1.1rem', fontWeight: 700, color: '#166534' }}>Loan Application Approved</h3>
            <p style={{ fontSize: '0.875rem', color: '#15803d', marginTop: '0.25rem' }}>
              {application.decision_reason || 'Congratulations! Your loan application has been approved by GenBank underwriting.'}
            </p>
          </div>
        </div>
      )}

      {/* Decision: Rejected */}
      {isRejected && (
        <div style={{ background: '#fef2f2', border: '1px solid #fca5a5', borderRadius: '12px', padding: '1.25rem 1.5rem', marginBottom: '1.5rem', display: 'flex', alignItems: 'center', gap: '1rem' }}>
          <AlertCircle size={32} color="#dc2626" style={{ flexShrink: 0 }} />
          <div>
            <h3 style={{ fontSize: '1.1rem', fontWeight: 700, color: '#991b1b' }}>Loan Application Declined</h3>
            <p style={{ fontSize: '0.875rem', color: '#b91c1c', marginTop: '0.25rem' }}>
              {application.decision_reason || 'Underwriting criteria were not met for this loan request.'}
            </p>
          </div>
        </div>
      )}

      {/* Decision: Escalated */}
      {isEscalated && (
        <div style={{ background: '#faf5ff', border: '1px solid #d8b4fe', borderRadius: '12px', padding: '1.25rem 1.5rem', marginBottom: '1.5rem', display: 'flex', alignItems: 'center', gap: '1rem' }}>
          <AlertCircle size={32} color="#9333ea" style={{ flexShrink: 0 }} />
          <div>
            <h3 style={{ fontSize: '1.1rem', fontWeight: 700, color: '#6b21a8' }}>Underwriting Escalation in Progress</h3>
            <p style={{ fontSize: '0.875rem', color: '#7e22ce', marginTop: '0.25rem' }}>
              Your application has been escalated to senior risk underwriting for comprehensive review.
            </p>
          </div>
        </div>
      )}

      {/* Post-submission Informative Banner (Standard) */}
      {!isDraft && !isDocsRequired && !isApproved && !isRejected && !isEscalated && (
        <div className="cust-info-card">
          <ShieldCheck size={24} color="#2563eb" />
          <div className="cust-info-text">
            <h3 className="cust-info-title">Application Under Active Underwriting</h3>
            <p className="cust-info-desc">
              Your application is currently undergoing autonomous verification and credit officer assessment.
              Any document follow-ups will be communicated directly in this workspace.
            </p>
          </div>
        </div>
      )}

      {/* Document Upload Center */}
      <div className="cust-docs-center">
        <div className="cust-docs-header">
          <div>
            <h2 className="cust-card-title">Supporting Financial Documentation</h2>
            <p className="cust-docs-subtitle">
              {isDraft
                ? 'Upload all mandatory documents to complete underwriting requirements. Accepted formats: PDF, PNG, JPG (up to 10MB).'
                : isDocsRequired
                ? 'Please upload the requested documents below. Once uploaded, your application will re-enter underwriting.'
                : 'Documents attached to this loan file. Document modification is locked post-submission.'}
            </p>
          </div>

          {isDraft && (
            <div className="cust-upload-progress">
              <span className="upload-progress-text">
                {docsList.length} of {REQUIRED_DOC_TYPES.length} Categories Attached
              </span>
            </div>
          )}
        </div>

        <div className="cust-doc-slots-grid">
          {REQUIRED_DOC_TYPES.map((req) => {
            const matchingDoc = docsList.find(
              (d) => (d.document_type || '').toUpperCase() === req.type
            );
            const isUploadingThis = uploadingSlot === req.type;

            return (
              <div
                key={req.type}
                className={`cust-doc-slot-card ${matchingDoc ? 'uploaded' : 'pending'}`}
              >
                <div className="slot-card-header">
                  <div className="slot-icon-box">
                    {matchingDoc ? (
                      <FileCheck2 size={22} color="#059669" />
                    ) : (
                      <UploadCloud size={22} color="#64748b" />
                    )}
                  </div>
                  <div className="slot-title-wrap">
                    <h3 className="slot-title">{req.label}</h3>
                    <span className="slot-type-pill">{req.type}</span>
                  </div>
                  {matchingDoc && (
                    <span className="slot-status-pill uploaded">
                      <CheckCircle2 size={12} /> Uploaded
                    </span>
                  )}
                  {!matchingDoc && (
                    <span className="slot-status-pill pending">
                      Not Uploaded
                    </span>
                  )}
                </div>

                <p className="slot-description">{req.description}</p>

                {matchingDoc ? (
                  <div className="slot-file-meta">
                    <div className="slot-meta-left">
                      <FileText size={16} className="text-slate-400" />
                      <span className="slot-filename" title={matchingDoc.original_filename}>
                        {matchingDoc.original_filename}
                      </span>
                      <span className="slot-filesize">
                        ({Math.round(matchingDoc.file_size / 1024)} KB)
                      </span>
                    </div>

                    {isDraft && (
                      <button
                        type="button"
                        onClick={() =>
                          handleDeleteDocument(matchingDoc.document_id, req.label)
                        }
                        className="slot-delete-btn"
                        title="Remove uploaded document"
                      >
                        <Trash2 size={14} />
                        <span>Remove</span>
                      </button>
                    )}

                    {isDocsRequired && (
                      <div style={{ marginLeft: 'auto' }}>
                        <input
                          type="file"
                          ref={(el) => (fileInputRefs.current[req.type] = el)}
                          style={{ display: 'none' }}
                          accept=".pdf,.png,.jpg,.jpeg"
                          onChange={(e) => {
                            if (e.target.files?.[0]) {
                              handleFileUpload(req.type, e.target.files[0]);
                            }
                          }}
                        />
                        <button
                          type="button"
                          disabled={isUploadingThis}
                          onClick={() => fileInputRefs.current[req.type]?.click()}
                          className="btn btn-secondary btn-sm"
                          style={{ fontSize: '0.75rem', padding: '0.25rem 0.6rem' }}
                        >
                          {isUploadingThis ? 'Uploading...' : 'Replace'}
                        </button>
                      </div>
                    )}
                  </div>
                ) : canUpload ? (
                  <div className="slot-upload-action">
                    <input
                      type="file"
                      ref={(el) => (fileInputRefs.current[req.type] = el)}
                      style={{ display: 'none' }}
                      accept=".pdf,.png,.jpg,.jpeg"
                      onChange={(e) => {
                        if (e.target.files?.[0]) {
                          handleFileUpload(req.type, e.target.files[0]);
                        }
                      }}
                    />
                    <button
                      type="button"
                      disabled={isUploadingThis || submittingApp}
                      onClick={() => fileInputRefs.current[req.type]?.click()}
                      className="slot-upload-btn"
                    >
                      {isUploadingThis ? (
                        <>
                          <Loader2 size={14} className="animate-spin" />
                          <span>Uploading...</span>
                        </>
                      ) : (
                        <>
                          <UploadCloud size={14} />
                          <span>{isDocsRequired ? 'Upload Requested Document' : 'Select Document File'}</span>
                        </>
                      )}
                    </button>
                  </div>
                ) : (
                  <div className="slot-missing-readonly">
                    <span>Document was not submitted during initial filing.</span>
                  </div>
                )}
              </div>
            );
          })}
        </div>

        {/* Submit Application CTA Footer (only in Draft) */}
        {isDraft && (
          <div className="cust-submit-section">
            <div className="submit-section-text">
              <h3 className="submit-section-title">Ready to Submit?</h3>
              <p className="submit-section-desc">
                {docsList.length === 0
                  ? 'Please attach at least one supporting financial document before submitting.'
                  : `You have uploaded ${docsList.length} document(s). Submitting will lock edits and trigger automated GenBank underwriting.`}
              </p>
            </div>

            <button
              type="button"
              disabled={docsList.length === 0 || submittingApp || uploadingSlot !== null}
              onClick={handleSubmitApplication}
              className="cust-submit-app-btn"
            >
              {submittingApp ? (
                <>
                  <Loader2 size={18} className="animate-spin" />
                  <span>Submitting & Triggering Underwriting...</span>
                </>
              ) : (
                <>
                  <Send size={18} />
                  <span>Submit Application for Underwriting</span>
                </>
              )}
            </button>
          </div>
        )}
      </div>

      <style>{`
        .cust-detail-container {
          display: flex;
          flex-direction: column;
          gap: 1.75rem;
        }

        .cust-detail-header-nav {
          display: flex;
          align-items: center;
        }

        .cust-back-link {
          display: inline-flex;
          align-items: center;
          gap: 0.375rem;
          color: #64748b;
          font-size: 0.875rem;
          font-weight: 500;
          text-decoration: none;
        }

        .cust-back-link:hover {
          color: #1e3a8a;
        }

        .cust-detail-hero {
          background: #ffffff;
          border: 1px solid #e2e8f0;
          border-radius: 12px;
          padding: 1.75rem;
          box-shadow: 0 1px 3px rgba(0, 0, 0, 0.02);
        }

        .cust-hero-main {
          display: flex;
          align-items: center;
          justify-content: space-between;
          flex-wrap: wrap;
          gap: 1rem;
          padding-bottom: 1.25rem;
          border-bottom: 1px solid #e2e8f0;
        }

        .cust-app-id-tag {
          font-size: 0.75rem;
          font-weight: 600;
          color: #64748b;
          text-transform: uppercase;
          letter-spacing: 0.05em;
        }

        .cust-app-number {
          font-size: 1.5rem;
          font-weight: 700;
          color: #0f172a;
          margin: 0.125rem 0 0 0;
          font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
        }

        .cust-hero-grid {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
          gap: 1.25rem;
          margin-top: 1.25rem;
        }

        .cust-hero-item {
          display: flex;
          flex-direction: column;
          gap: 0.25rem;
        }

        .hero-label {
          font-size: 0.75rem;
          font-weight: 500;
          color: #64748b;
        }

        .hero-val {
          font-size: 1rem;
          font-weight: 600;
          color: #0f172a;
        }

        .cust-error-banner, .cust-success-banner {
          display: flex;
          align-items: center;
          gap: 0.75rem;
          padding: 0.875rem 1.25rem;
          border-radius: 8px;
          font-size: 0.875rem;
        }

        .cust-error-banner {
          background: #fef2f2;
          border: 1px solid #fecaca;
          color: #991b1b;
        }

        .cust-success-banner {
          background: #ecfdf5;
          border: 1px solid #a7f3d0;
          color: #065f46;
        }

        .cust-stepper-card {
          background: #ffffff;
          border: 1px solid #e2e8f0;
          border-radius: 12px;
          padding: 1.5rem;
        }

        .cust-card-title {
          font-size: 1.125rem;
          font-weight: 700;
          color: #0f172a;
          margin: 0 0 1rem 0;
        }

        .cust-stepper {
          display: flex;
          align-items: center;
          justify-content: space-between;
          position: relative;
          gap: 0.5rem;
          overflow-x: auto;
          padding: 0.5rem 0;
        }

        .stepper-step {
          display: flex;
          align-items: center;
          gap: 0.75rem;
          min-width: 140px;
        }

        .step-indicator {
          width: 32px;
          height: 32px;
          border-radius: 50%;
          display: flex;
          align-items: center;
          justify-content: center;
          font-size: 0.875rem;
          font-weight: 600;
          background: #f1f5f9;
          color: #64748b;
          flex-shrink: 0;
        }

        .stepper-step.active .step-indicator {
          background: #eff6ff;
          color: #2563eb;
          border: 2px solid #2563eb;
        }

        .stepper-step.completed .step-indicator {
          background: #ecfdf5;
          color: #059669;
        }

        .step-content {
          display: flex;
          flex-direction: column;
        }

        .step-title {
          font-size: 0.8125rem;
          font-weight: 600;
          color: #0f172a;
        }

        .step-desc {
          font-size: 0.6875rem;
          color: #64748b;
        }

        .stepper-line {
          flex: 1;
          height: 2px;
          background: #e2e8f0;
          min-width: 24px;
        }

        .stepper-line.completed {
          background: #059669;
        }

        .cust-info-card {
          display: flex;
          align-items: flex-start;
          gap: 1rem;
          background: #eff6ff;
          border: 1px solid #bfdbfe;
          border-radius: 10px;
          padding: 1.25rem;
        }

        .cust-info-title {
          font-size: 0.9375rem;
          font-weight: 700;
          color: #1e3a8a;
          margin: 0 0 0.25rem 0;
        }

        .cust-info-desc {
          font-size: 0.8125rem;
          color: #1e40af;
          margin: 0;
          line-height: 1.4;
        }

        .cust-docs-center {
          background: #ffffff;
          border: 1px solid #e2e8f0;
          border-radius: 12px;
          padding: 1.75rem;
          display: flex;
          flex-direction: column;
          gap: 1.5rem;
        }

        .cust-docs-header {
          display: flex;
          align-items: flex-start;
          justify-content: space-between;
          flex-wrap: wrap;
          gap: 1rem;
        }

        .cust-docs-subtitle {
          font-size: 0.8125rem;
          color: #64748b;
          margin: 0.25rem 0 0 0;
        }

        .upload-progress-text {
          font-size: 0.75rem;
          font-weight: 600;
          background: #f1f5f9;
          padding: 0.375rem 0.75rem;
          border-radius: 16px;
          color: #334155;
        }

        .cust-doc-slots-grid {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
          gap: 1.25rem;
        }

        .cust-doc-slot-card {
          border: 1px solid #e2e8f0;
          border-radius: 10px;
          padding: 1.25rem;
          display: flex;
          flex-direction: column;
          gap: 0.875rem;
          background: #ffffff;
          transition: border-color 0.15s ease;
        }

        .cust-doc-slot-card.uploaded {
          border-color: #a7f3d0;
          background: #fcfdfd;
        }

        .slot-card-header {
          display: flex;
          align-items: center;
          gap: 0.75rem;
        }

        .slot-icon-box {
          width: 36px;
          height: 36px;
          border-radius: 8px;
          background: #f8fafc;
          display: flex;
          align-items: center;
          justify-content: center;
          flex-shrink: 0;
        }

        .slot-title-wrap {
          display: flex;
          flex-direction: column;
          flex: 1;
        }

        .slot-title {
          font-size: 0.875rem;
          font-weight: 700;
          color: #0f172a;
          margin: 0;
        }

        .slot-type-pill {
          font-size: 0.6875rem;
          color: #64748b;
          font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, monospace;
        }

        .slot-status-pill {
          display: inline-flex;
          align-items: center;
          gap: 0.25rem;
          font-size: 0.6875rem;
          font-weight: 600;
          padding: 0.125rem 0.5rem;
          border-radius: 12px;
        }

        .slot-status-pill.uploaded {
          background: #ecfdf5;
          color: #059669;
        }

        .slot-status-pill.pending {
          background: #f1f5f9;
          color: #64748b;
        }

        .slot-description {
          font-size: 0.75rem;
          color: #64748b;
          line-height: 1.4;
          margin: 0;
        }

        .slot-file-meta {
          display: flex;
          align-items: center;
          justify-content: space-between;
          background: #f8fafc;
          padding: 0.5rem 0.75rem;
          border-radius: 6px;
          border: 1px solid #e2e8f0;
          gap: 0.5rem;
        }

        .slot-meta-left {
          display: flex;
          align-items: center;
          gap: 0.375rem;
          overflow: hidden;
        }

        .slot-filename {
          font-size: 0.75rem;
          font-weight: 600;
          color: #1e293b;
          white-space: nowrap;
          overflow: hidden;
          text-overflow: ellipsis;
          max-width: 150px;
        }

        .slot-filesize {
          font-size: 0.6875rem;
          color: #94a3b8;
          white-space: nowrap;
        }

        .slot-delete-btn {
          display: inline-flex;
          align-items: center;
          gap: 0.25rem;
          background: none;
          border: none;
          color: #dc2626;
          font-size: 0.75rem;
          font-weight: 600;
          cursor: pointer;
          padding: 0.25rem 0.5rem;
          border-radius: 4px;
        }

        .slot-delete-btn:hover {
          background: #fee2e2;
        }

        .slot-upload-btn {
          width: 100%;
          display: flex;
          align-items: center;
          justify-content: center;
          gap: 0.5rem;
          padding: 0.625rem 1rem;
          background: #f8fafc;
          border: 1px dashed #cbd5e1;
          border-radius: 6px;
          color: #2563eb;
          font-size: 0.8125rem;
          font-weight: 600;
          cursor: pointer;
          transition: all 0.15s ease;
        }

        .slot-upload-btn:hover:not(:disabled) {
          background: #eff6ff;
          border-color: #2563eb;
        }

        .slot-upload-btn:disabled {
          opacity: 0.5;
          cursor: not-allowed;
        }

        .slot-missing-readonly {
          font-size: 0.75rem;
          color: #94a3b8;
          font-style: italic;
        }

        .cust-submit-section {
          display: flex;
          align-items: center;
          justify-content: space-between;
          flex-wrap: wrap;
          gap: 1rem;
          padding-top: 1.5rem;
          border-top: 1px solid #e2e8f0;
        }

        .submit-section-title {
          font-size: 1rem;
          font-weight: 700;
          color: #0f172a;
          margin: 0 0 0.25rem 0;
        }

        .submit-section-desc {
          font-size: 0.8125rem;
          color: #64748b;
          margin: 0;
        }

        .cust-submit-app-btn {
          display: inline-flex;
          align-items: center;
          gap: 0.625rem;
          background: #059669;
          color: #ffffff;
          padding: 0.75rem 1.5rem;
          border-radius: 8px;
          font-size: 0.875rem;
          font-weight: 600;
          border: none;
          cursor: pointer;
          transition: background 0.15s ease;
          box-shadow: 0 2px 4px rgba(5, 150, 105, 0.2);
        }

        .cust-submit-app-btn:hover:not(:disabled) {
          background: #047857;
        }

        .cust-submit-app-btn:disabled {
          opacity: 0.5;
          cursor: not-allowed;
        }

        .cust-error-page {
          background: #ffffff;
          border: 1px solid #e2e8f0;
          border-radius: 12px;
          padding: 3rem;
          text-align: center;
          display: flex;
          flex-direction: column;
          align-items: center;
          gap: 1rem;
        }
      `}</style>
    </div>
  );
}

export default CustomerApplicationDetailPage;
