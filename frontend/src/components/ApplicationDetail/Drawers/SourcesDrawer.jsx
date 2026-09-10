import React, { useState, useEffect } from 'react';
import {
  FileText,
  Landmark,
  ReceiptText,
  BadgeCheck,
  ChevronRight,
  BookOpen,
  CheckCircle2,
  FileCode,
} from 'lucide-react';
import { api } from '../../../services/api';
import { formatDateTime, formatPolicySourceLabel } from '../../../services/formatters';

export function SourcesDrawer({
  application,
  documents = [],
  agentReview: initialAgentReview,
  applicationId,
  onSelectDocument,
}) {
  const [internalReview, setInternalReview] = useState(null);

  useEffect(() => {
    if (!initialAgentReview && (applicationId || application?.application_id)) {
      api.getAgentReview(applicationId || application?.application_id)
        .then((res) => setInternalReview(res))
        .catch(() => {});
    }
  }, [initialAgentReview, applicationId, application?.application_id]);

  const agentReview = initialAgentReview || internalReview;
  const citations =
    agentReview?.final_review?.policy_references ||
    agentReview?.policy_references ||
    agentReview?.policy_citations ||
    [];

  return (
    <div className="sources-drawer-wrap">
      <div style={{ marginBottom: '1.25rem' }}>
        <p style={{ fontSize: '0.825rem', color: 'var(--color-text-secondary)', lineHeight: 1.45 }}>
          Originating evidentiary records and regulatory policies used to compile the application assessment.
        </p>
      </div>

      {/* Primary Application Record */}
      <div style={{ marginBottom: '1.5rem' }}>
        <h4 style={{ fontSize: '0.8rem', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.04em', color: 'var(--color-text-muted)', marginBottom: '0.5rem' }}>
          Application Record
        </h4>
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            padding: '0.75rem 1rem',
            background: '#f8fafc',
            border: '1px solid var(--color-border)',
            borderRadius: 'var(--radius-md)',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
            <FileCode size={18} color="var(--color-primary-600)" />
            <div>
              <div style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--color-text-primary)' }}>
                Loan Application {application?.application_id}
              </div>
              <div style={{ fontSize: '0.75rem', color: 'var(--color-text-muted)' }}>
                Primary profile: {application?.applicant_name} • Submitted {formatDateTime(application?.created_at)}
              </div>
            </div>
          </div>
          <span className="badge badge-low" style={{ fontSize: '0.7rem' }}>VERIFIED</span>
        </div>
      </div>

      {/* Submitted Supporting Documents */}
      <div style={{ marginBottom: '1.5rem' }}>
        <h4 style={{ fontSize: '0.8rem', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.04em', color: 'var(--color-text-muted)', marginBottom: '0.5rem' }}>
          Submitted Documents ({documents.length})
        </h4>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
          {documents.length === 0 ? (
            <div style={{ padding: '1rem', textAlign: 'center', color: 'var(--color-text-muted)', fontSize: '0.825rem' }}>
              No documents uploaded.
            </div>
          ) : (
            documents.map((doc) => {
              const type = (doc.document_type || '').toUpperCase();
              const filename = doc.original_filename || '';
              const isKyc = type === 'KYC' || filename.toLowerCase().includes('kyc') || filename.toLowerCase().includes('aadhaar');
              const isPayslip = type === 'PAYSLIP' || filename.toLowerCase().includes('payslip');
              const isBank = type === 'BANK_STATEMENT' || filename.toLowerCase().includes('bank');

              let Icon = FileText;
              let label = 'Document';
              if (isKyc) { Icon = BadgeCheck; label = 'KYC Document (Identity)'; }
              else if (isPayslip) { Icon = FileText; label = 'Salary Payslip'; }
              else if (isBank) { Icon = Landmark; label = 'Bank Statement'; }
              else { Icon = ReceiptText; label = 'Tax Return (ITR-V)'; }

              return (
                <div
                  key={doc.document_id}
                  onClick={() => onSelectDocument && onSelectDocument(doc)}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    padding: '0.75rem 1rem',
                    background: '#ffffff',
                    border: '1px solid var(--color-border)',
                    borderRadius: 'var(--radius-md)',
                    cursor: 'pointer',
                    transition: 'border-color 0.15s ease, background 0.15s ease',
                  }}
                  onMouseEnter={(e) => { e.currentTarget.style.background = '#f8fafc'; e.currentTarget.style.borderColor = 'var(--color-primary-500)'; }}
                  onMouseLeave={(e) => { e.currentTarget.style.background = '#ffffff'; e.currentTarget.style.borderColor = 'var(--color-border)'; }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
                    <Icon size={18} color="var(--color-primary-600)" />
                    <div>
                      <div style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--color-text-primary)' }}>
                        {label}
                      </div>
                      <div style={{ fontSize: '0.725rem', color: 'var(--color-text-muted)', fontFamily: 'var(--font-mono)' }}>
                        {doc.original_filename}
                      </div>
                    </div>
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', color: 'var(--color-primary-600)', fontSize: '0.775rem', fontWeight: 600 }}>
                    <span>View</span>
                    <ChevronRight size={14} />
                  </div>
                </div>
              );
            })
          )}
        </div>
      </div>

      {/* Regulatory & Bank Policy Provenance */}
      <div>
        <h4 style={{ fontSize: '0.8rem', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.04em', color: 'var(--color-text-muted)', marginBottom: '0.5rem' }}>
          Policy Provenance {citations.length > 0 && `(${citations.length})`}
        </h4>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
          {citations.length === 0 ? (
            <div style={{ padding: '1rem', textAlign: 'center', color: 'var(--color-text-muted)', fontSize: '0.825rem', background: '#f8fafc', border: '1px dashed var(--color-border)', borderRadius: 'var(--radius-md)' }}>
              No policy citations referenced for this application.
            </div>
          ) : (
            citations.map((c, idx) => {
              const label = formatPolicySourceLabel(c);
              const isRBI = label === 'RBI';
              const policyTitle =
                c.policy_name || c.title || c.section_title || c.policy_id || 'Underwriting Standard';
              const policyId = c.policy_id || null;
              const text =
                c.citation_text || c.content || c.snippet || c.rule_summary || '';

              return (
                <div
                  key={policyId || idx}
                  style={{
                    padding: '0.75rem 1rem',
                    background: isRBI ? '#f0f9ff' : '#f8fafc',
                    border: isRBI ? '1px solid #bae6fd' : '1px solid var(--color-border)',
                    borderRadius: 'var(--radius-md)',
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '0.4rem', marginBottom: '0.2rem' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                      <span className={`badge ${isRBI ? 'badge-info' : 'badge-neutral'}`} style={{ fontSize: '0.675rem' }}>
                        [{label}]
                      </span>
                      <div style={{ fontSize: '0.825rem', fontWeight: 600, color: 'var(--color-text-primary)' }}>
                        {policyTitle}
                      </div>
                    </div>
                    {policyId && (
                      <span style={{ fontSize: '0.675rem', color: 'var(--color-text-muted)', fontFamily: 'var(--font-mono)' }}>
                        {policyId}
                      </span>
                    )}
                  </div>
                  {text && (
                    <p style={{ fontSize: '0.75rem', color: 'var(--color-text-secondary)', margin: 0, lineHeight: 1.45 }}>
                      {text}
                    </p>
                  )}
                </div>
              );
            })
          )}
        </div>
      </div>
    </div>
  );
}

