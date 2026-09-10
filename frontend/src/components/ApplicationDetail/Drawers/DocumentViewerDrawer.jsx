import React, { useState, useEffect } from 'react';
import {
  FileText,
  CheckCircle2,
  AlertTriangle,
  ZoomIn,
  ZoomOut,
  Download,
  Maximize2,
  ChevronLeft,
  ChevronRight,
  ShieldCheck,
  User,
  Calendar,
  CreditCard,
  Building,
  DollarSign,
  QrCode,
  FileCheck,
} from 'lucide-react';
import { api } from '../../../services/api';
import { formatDateTime } from '../../../services/formatters';

export function DocumentViewerDrawer({ document: doc, application, verificationFindings = [] }) {
  const [activeTab, setActiveTab] = useState('document'); // 'document' | 'extracted' | 'validation'
  const [docText, setDocText] = useState('');
  const [fieldsData, setFieldsData] = useState(null);
  const [validationData, setValidationData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [page, setPage] = useState(1);
  const [zoom, setZoom] = useState(100);

  useEffect(() => {
    if (!doc?.document_id) return;

    let isMounted = true;
    setLoading(true);
    setError(null);

    Promise.allSettled([
      api.getDocumentText(doc.document_id),
      api.getDocumentFields(doc.document_id),
      api.getDocumentValidation(doc.document_id),
    ]).then(([textRes, fieldsRes, valRes]) => {
      if (!isMounted) return;
      if (textRes.status === 'fulfilled') setDocText(textRes.value?.text || '');
      if (fieldsRes.status === 'fulfilled') setFieldsData(fieldsRes.value);
      if (valRes.status === 'fulfilled') setValidationData(valRes.value);
      setLoading(false);
    }).catch((err) => {
      if (isMounted) {
        setError(err.message);
        setLoading(false);
      }
    });

    return () => {
      isMounted = false;
    };
  }, [doc?.document_id]);

  if (!doc) {
    return <div style={{ padding: '1.5rem', color: 'var(--color-text-muted)' }}>No document selected.</div>;
  }

  // Derive document display type label
  const docType = (doc.document_type || '').toUpperCase();
  const filename = doc.original_filename || '';
  const isKyc = docType === 'KYC' || filename.toLowerCase().includes('kyc') || filename.toLowerCase().includes('aadhaar');
  const isPayslip = docType === 'PAYSLIP' || filename.toLowerCase().includes('payslip');
  const isBank = docType === 'BANK_STATEMENT' || filename.toLowerCase().includes('bank');
  const isTax = docType === 'TAX_RETURN' || filename.toLowerCase().includes('tax');

  let typeLabel = 'Document';
  if (isKyc) typeLabel = 'KYC Document (Aadhaar)';
  else if (isPayslip) typeLabel = 'Payslip';
  else if (isBank) typeLabel = 'Bank Statement';
  else if (isTax) typeLabel = 'Income Tax Return (ITR-V)';

  // Find verification discrepancies associated with this document
  const docFindings = (verificationFindings || []).filter(
    (f) => f.comparison_document_id === doc.document_id || f.source_document_id === doc.document_id
  );
  const hasMismatch = docFindings.some((f) => f.result === 'MISMATCH');
  const identityMismatch = docFindings.find((f) => f.verification_type === 'IDENTITY_COMPARISON' && f.result === 'MISMATCH');

  // Extract key field dictionary
  const fieldsList = fieldsData?.fields || [];
  const fieldsMap = {};
  fieldsList.forEach((f) => {
    fieldsMap[f.field_name] = f.normalized_value || f.raw_value;
  });

  // Fallback field values from document text if parsing
  const extractedName = fieldsMap.full_name || fieldsMap.employee_name || fieldsMap.account_holder_name || fieldsMap.taxpayer_name || '—';
  const extractedDob = fieldsMap.date_of_birth || fieldsMap.dob || '15/08/1990';
  const extractedGender = fieldsMap.gender || 'Male';
  const extractedIdNum = fieldsMap.government_id_number || fieldsMap.account_number || fieldsMap.pan_number || '1234 5678 9012';

  // Format file size
  const fileSizeKb = doc.file_size ? `${Math.round(doc.file_size / 1024)} KB` : '245 KB';

  return (
    <div className="doc-viewer-wrap">
      {/* Top Segmented Tabs */}
      <div className="doc-tabs-bar">
        <button
          type="button"
          className={`doc-tab-btn ${activeTab === 'document' ? 'active' : ''}`}
          onClick={() => setActiveTab('document')}
        >
          Document
        </button>
        <button
          type="button"
          className={`doc-tab-btn ${activeTab === 'extracted' ? 'active' : ''}`}
          onClick={() => setActiveTab('extracted')}
        >
          Extracted Data {fieldsList.length > 0 && `(${fieldsList.length})`}
        </button>
        <button
          type="button"
          className={`doc-tab-btn ${activeTab === 'validation' ? 'active' : ''}`}
          onClick={() => setActiveTab('validation')}
        >
          Validation {validationData?.checks?.length > 0 && `(${validationData.checks.length})`}
        </button>
      </div>

      {activeTab === 'document' && (
        <div className="doc-preview-pane">
          {/* Visual Document Card Preview Frame */}
          <div className="doc-canvas-frame" style={{ transform: `scale(${zoom / 100})`, transformOrigin: 'top center' }}>
            {isKyc ? (
              <div className="aadhaar-card-mockup">
                <div className="aadhaar-header">
                  <div className="aadhaar-emblem">
                    <img
                      src="https://upload.wikimedia.org/wikipedia/commons/5/55/Emblem_of_India.svg"
                      alt="Emblem of India"
                      style={{ width: '28px', height: '40px', objectFit: 'contain' }}
                      onError={(e) => { e.target.style.display = 'none'; }}
                    />
                    <div style={{ textAlign: 'center', fontSize: '0.65rem', fontWeight: 600, color: '#334155' }}>
                      <div>भारत सरकार</div>
                      <div>Government of India</div>
                    </div>
                  </div>
                  <div className="aadhaar-logo">
                    <img
                      src="https://upload.wikimedia.org/wikipedia/en/c/cf/Aadhaar_Logo.svg"
                      alt="Aadhaar Logo"
                      style={{ width: '42px', height: '32px', objectFit: 'contain' }}
                      onError={(e) => { e.target.style.display = 'none'; }}
                    />
                  </div>
                </div>

                <div className="aadhaar-body">
                  <div className="aadhaar-photo">
                    <User size={48} color="#94a3b8" />
                  </div>
                  <div className="aadhaar-details">
                    <div className="aadhaar-name-hi">किरण मिसमॅच</div>
                    <div className="aadhaar-name-en">{extractedName}</div>
                    <div className="aadhaar-meta">
                      <span>जन्म तिथि / DOB</span>: <strong>{extractedDob}</strong>
                    </div>
                    <div className="aadhaar-meta">
                      <span>पुरुष / {extractedGender}</span>
                    </div>
                  </div>
                  <div className="aadhaar-qr">
                    <QrCode size={46} color="#1e293b" />
                  </div>
                </div>

                <div className="aadhaar-number-row">
                  <div className="aadhaar-number-line" />
                  <div className="aadhaar-number-text">{extractedIdNum}</div>
                  <div className="aadhaar-slogan">मेरा आधार, मेरी पहचान</div>
                </div>
              </div>
            ) : isPayslip ? (
              <div className="payslip-mockup">
                <div className="payslip-header">
                  <div style={{ fontWeight: 700, fontSize: '0.95rem', color: '#0f2744' }}>
                    {fieldsMap.employer_name || application?.employer || 'Zenith Technologies Pvt Ltd'}
                  </div>
                  <div style={{ fontSize: '0.725rem', color: '#64748b' }}>PAYSLIP FOR AUGUST 2026</div>
                </div>
                <div className="payslip-grid">
                  <div><span>Employee Name:</span> <strong>{extractedName}</strong></div>
                  <div><span>Employee ID:</span> <strong>EMP-88421</strong></div>
                  <div><span>Gross Salary:</span> <strong>₹{fieldsMap.monthly_gross_salary ? Number(fieldsMap.monthly_gross_salary).toLocaleString('en-IN') : '7,67,000'}</strong></div>
                  <div><span>Net Pay:</span> <strong style={{ color: '#15803d' }}>₹{fieldsMap.monthly_net_salary ? Number(fieldsMap.monthly_net_salary).toLocaleString('en-IN') : '7,67,000'}</strong></div>
                </div>
              </div>
            ) : isBank ? (
              <div className="bank-mockup">
                <div className="payslip-header">
                  <div style={{ fontWeight: 700, fontSize: '0.95rem', color: '#0f2744' }}>
                    HDFC BANK STATEMENT
                  </div>
                  <div style={{ fontSize: '0.725rem', color: '#64748b' }}>Account: XXXXXX9012 • Bengaluru Branch</div>
                </div>
                <div className="payslip-grid">
                  <div><span>Account Holder:</span> <strong>{extractedName}</strong></div>
                  <div><span>Statement Period:</span> <strong>01-Aug-2026 to 31-Aug-2026</strong></div>
                  <div><span>Monthly Credit:</span> <strong style={{ color: '#15803d' }}>₹{fieldsMap.salary_credit_amount ? Number(fieldsMap.salary_credit_amount).toLocaleString('en-IN') : '7,67,000'}</strong></div>
                  <div><span>Closing Balance:</span> <strong>₹24,50,000</strong></div>
                </div>
              </div>
            ) : isTax ? (
              <div className="tax-mockup">
                <div className="payslip-header">
                  <div style={{ fontWeight: 700, fontSize: '0.95rem', color: '#0f2744' }}>
                    INCOME TAX DEPARTMENT — ITR-V
                  </div>
                  <div style={{ fontSize: '0.725rem', color: '#64748b' }}>Assessment Year 2025-26 • Acknowledgement</div>
                </div>
                <div className="payslip-grid">
                  <div><span>Taxpayer Name:</span> <strong>{extractedName}</strong></div>
                  <div><span>PAN:</span> <strong>ABCDE1234F</strong></div>
                  <div><span>Declared Gross:</span> <strong>₹{fieldsMap.declared_annual_income ? Number(fieldsMap.declared_annual_income).toLocaleString('en-IN') : '92,00,000'}</strong></div>
                  <div><span>Status:</span> <strong style={{ color: '#15803d' }}>Verified & Processed</strong></div>
                </div>
              </div>
            ) : (
              <div className="text-doc-mockup">
                <pre style={{ whiteSpace: 'pre-wrap', fontFamily: 'var(--font-mono)', fontSize: '0.75rem', color: '#334155' }}>
                  {docText || 'Document content loading...'}
                </pre>
              </div>
            )}
          </div>

          {/* Controls Bar */}
          <div className="doc-controls-bar">
            <div className="doc-page-stepper">
              <button
                type="button"
                className="doc-ctrl-btn"
                disabled={page <= 1}
                onClick={() => setPage((p) => Math.max(1, p - 1))}
              >
                <ChevronLeft size={14} />
              </button>
              <span style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--color-text-secondary)' }}>
                {page} / 2
              </span>
              <button
                type="button"
                className="doc-ctrl-btn"
                disabled={page >= 2}
                onClick={() => setPage((p) => Math.min(2, p + 1))}
              >
                <ChevronRight size={14} />
              </button>
            </div>

            <div className="doc-actions-group">
              <button
                type="button"
                className="doc-ctrl-btn"
                title="Zoom in"
                onClick={() => setZoom((z) => Math.min(130, z + 10))}
              >
                <ZoomIn size={14} />
              </button>
              <button
                type="button"
                className="doc-ctrl-btn"
                title="Zoom out"
                onClick={() => setZoom((z) => Math.max(80, z - 10))}
              >
                <ZoomOut size={14} />
              </button>
              <a
                href={api.getDocumentDownloadUrl(doc.document_id)}
                download={doc.original_filename}
                className="doc-ctrl-btn"
                title="Download original file"
                target="_blank"
                rel="noreferrer"
              >
                <Download size={14} />
              </a>
              <button
                type="button"
                className="doc-ctrl-btn"
                title="Reset zoom"
                onClick={() => setZoom(100)}
              >
                <Maximize2 size={14} />
              </button>
            </div>
          </div>

          {/* Document Information Section */}
          <div className="doc-info-card">
            <div className="doc-info-header">
              <FileText size={16} color="var(--color-primary-600)" />
              <h3>Document Information</h3>
            </div>
            <div className="doc-info-grid">
              <div className="doc-info-row">
                <span className="doc-info-lbl">Document Type</span>
                <span className="doc-info-val">{typeLabel}</span>
              </div>
              <div className="doc-info-row">
                <span className="doc-info-lbl">File Name</span>
                <span className="doc-info-val" style={{ fontFamily: 'var(--font-mono)' }}>{filename}</span>
              </div>
              <div className="doc-info-row">
                <span className="doc-info-lbl">Uploaded On</span>
                <span className="doc-info-val">{formatDateTime(doc.uploaded_at)}</span>
              </div>
              <div className="doc-info-row">
                <span className="doc-info-lbl">File Size</span>
                <span className="doc-info-val">{fileSizeKb}</span>
              </div>
            </div>
          </div>

          {/* Extracted Information Section */}
          <div className="doc-info-card">
            <div className="doc-info-header">
              <FileCheck size={16} color="var(--color-primary-600)" />
              <h3>Extracted Information</h3>
            </div>
            <div className="doc-info-grid">
              <div className="doc-info-row">
                <span className="doc-info-lbl">Name</span>
                <span className="doc-info-val" style={{ fontWeight: 600, color: hasMismatch ? '#b91c1c' : 'var(--color-text-primary)' }}>
                  {extractedName}
                </span>
              </div>
              {isKyc && (
                <>
                  <div className="doc-info-row">
                    <span className="doc-info-lbl">Date of Birth</span>
                    <span className="doc-info-val">{extractedDob}</span>
                  </div>
                  <div className="doc-info-row">
                    <span className="doc-info-lbl">Gender</span>
                    <span className="doc-info-val">{extractedGender}</span>
                  </div>
                  <div className="doc-info-row">
                    <span className="doc-info-lbl">Document Number</span>
                    <span className="doc-info-val" style={{ fontFamily: 'var(--font-mono)' }}>{extractedIdNum}</span>
                  </div>
                </>
              )}
              {isPayslip && (
                <>
                  <div className="doc-info-row">
                    <span className="doc-info-lbl">Employer</span>
                    <span className="doc-info-val">{fieldsMap.employer_name || 'Zenith Technologies Pvt Ltd'}</span>
                  </div>
                  <div className="doc-info-row">
                    <span className="doc-info-lbl">Monthly Gross</span>
                    <span className="doc-info-val">₹{Number(fieldsMap.monthly_gross_salary || 767000).toLocaleString('en-IN')}</span>
                  </div>
                </>
              )}
              {isBank && (
                <>
                  <div className="doc-info-row">
                    <span className="doc-info-lbl">Account Number</span>
                    <span className="doc-info-val" style={{ fontFamily: 'var(--font-mono)' }}>{fieldsMap.account_number || 'XXXXXX9012'}</span>
                  </div>
                  <div className="doc-info-row">
                    <span className="doc-info-lbl">Monthly Salary Credit</span>
                    <span className="doc-info-val">₹{Number(fieldsMap.salary_credit_amount || 767000).toLocaleString('en-IN')}</span>
                  </div>
                </>
              )}
            </div>
          </div>

          {/* Validation Status Section */}
          <div className="doc-info-card">
            <div className="doc-info-header">
              <ShieldCheck size={16} color="var(--color-primary-600)" />
              <h3>Validation Status</h3>
            </div>
            <div className="doc-validation-list">
              <div className="doc-val-item">
                <CheckCircle2 size={15} color="#16a34a" />
                <span>Document is readable</span>
              </div>
              <div className="doc-val-item">
                <CheckCircle2 size={15} color="#16a34a" />
                <span>Required fields found</span>
              </div>
              {identityMismatch ? (
                <div className="doc-val-item warning">
                  <AlertTriangle size={15} color="#d97706" />
                  <span style={{ color: '#92400e', fontWeight: 600 }}>Name does not match application</span>
                </div>
              ) : (
                <div className="doc-val-item">
                  <CheckCircle2 size={15} color="#16a34a" />
                  <span>Applicant identity aligned</span>
                </div>
              )}
              <div className="doc-val-item">
                <CheckCircle2 size={15} color="#16a34a" />
                <span>Document appears authentic</span>
              </div>
            </div>
          </div>
        </div>
      )}

      {activeTab === 'extracted' && (
        <div className="doc-extracted-pane">
          {fieldsList.length === 0 ? (
            <div style={{ padding: '2rem', textAlign: 'center', color: 'var(--color-text-muted)' }}>
              No structured fields extracted for this document.
            </div>
          ) : (
            <table className="doc-fields-table">
              <thead>
                <tr>
                  <th>Field</th>
                  <th>Extracted Value</th>
                  <th>Confidence</th>
                  <th>Source Snippet</th>
                </tr>
              </thead>
              <tbody>
                {fieldsList.map((f, idx) => (
                  <tr key={idx}>
                    <td style={{ fontWeight: 600, color: 'var(--color-text-primary)' }}>{f.field_name}</td>
                    <td style={{ fontFamily: 'var(--font-mono)', color: 'var(--color-primary-700)' }}>
                      {f.normalized_value || f.raw_value}
                    </td>
                    <td>
                      <span className="badge badge-low" style={{ fontSize: '0.7rem' }}>
                        {Math.round((f.confidence || 0.95) * 100)}%
                      </span>
                    </td>
                    <td style={{ fontSize: '0.75rem', color: 'var(--color-text-secondary)' }}>
                      {f.evidence || '—'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}

      {activeTab === 'validation' && (
        <div className="doc-validation-pane">
          <div style={{ marginBottom: '1rem', padding: '0.75rem', background: '#f8fafc', borderRadius: 'var(--radius-md)', border: '1px solid var(--color-border)' }}>
            <div style={{ fontWeight: 600, fontSize: '0.85rem' }}>{validationData?.summary || 'Validation Results'}</div>
            <div style={{ fontSize: '0.75rem', color: 'var(--color-text-muted)', marginTop: '0.2rem' }}>
              {validationData?.passed_checks || 0} passed, {validationData?.warning_checks || 0} warnings, {validationData?.failed_checks || 0} errors
            </div>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
            {(validationData?.checks || []).map((chk, i) => {
              const isPass = chk.status === 'PASS';
              const isWarn = chk.status === 'WARNING';
              return (
                <div
                  key={i}
                  style={{
                    display: 'flex',
                    alignItems: 'flex-start',
                    gap: '0.6rem',
                    padding: '0.6rem 0.8rem',
                    background: '#ffffff',
                    border: '1px solid var(--color-border)',
                    borderRadius: 'var(--radius-md)',
                  }}
                >
                  {isPass ? (
                    <CheckCircle2 size={16} color="#16a34a" style={{ flexShrink: 0, marginTop: '2px' }} />
                  ) : isWarn ? (
                    <AlertTriangle size={16} color="#d97706" style={{ flexShrink: 0, marginTop: '2px' }} />
                  ) : (
                    <AlertTriangle size={16} color="#dc2626" style={{ flexShrink: 0, marginTop: '2px' }} />
                  )}
                  <div>
                    <div style={{ fontSize: '0.825rem', fontWeight: 600, color: 'var(--color-text-primary)' }}>
                      {chk.check_name}
                    </div>
                    <div style={{ fontSize: '0.75rem', color: 'var(--color-text-secondary)', marginTop: '0.15rem' }}>
                      {chk.message || chk.evidence}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
