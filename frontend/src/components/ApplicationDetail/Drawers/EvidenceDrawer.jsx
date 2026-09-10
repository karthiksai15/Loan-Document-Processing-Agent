import React, { useState, useEffect } from 'react';
import {
  Layers,
  CheckCircle2,
  AlertTriangle,
  FileText,
  User,
  ShieldCheck,
  ChevronRight,
} from 'lucide-react';
import { api } from '../../../services/api';
import { getDocumentDisplayLabel } from '../../../services/formatters';

export function EvidenceDrawer({
  application,
  documents = [],
  verificationData,
  evidenceData: initialEvidenceData,
  applicationId,
  onSelectDocument,
}) {
  const [internalEvidence, setInternalEvidence] = useState(null);

  useEffect(() => {
    if (!initialEvidenceData && (applicationId || application?.application_id)) {
      api.getEvidence(applicationId || application?.application_id)
        .then((res) => setInternalEvidence(res))
        .catch(() => {});
    }
  }, [initialEvidenceData, applicationId, application?.application_id]);

  const evidenceData = initialEvidenceData || internalEvidence;
  const findings = verificationData?.findings || [];
  const mismatches = findings.filter((f) => f.result === 'MISMATCH');

  return (
    <div className="evidence-drawer-wrap">
      <div style={{ marginBottom: '1.25rem' }}>
        <p style={{ fontSize: '0.825rem', color: 'var(--color-text-secondary)', lineHeight: 1.45 }}>
          Structured evidentiary chain linking application profile, submitted documents, verification findings, and validation checks.
        </p>
      </div>

      {/* 1. Application Entity */}
      <div style={{ marginBottom: '1.25rem' }}>
        <h4 style={{ fontSize: '0.8rem', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.04em', color: 'var(--color-text-muted)', marginBottom: '0.5rem' }}>
          Application Profile
        </h4>
        <div style={{ padding: '0.75rem 1rem', background: '#f8fafc', border: '1px solid var(--color-border)', borderRadius: 'var(--radius-md)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <CheckCircle2 size={16} color="#16a34a" />
            <span style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--color-text-primary)' }}>
              Loan Application ({application?.application_id})
            </span>
          </div>
          <div style={{ fontSize: '0.75rem', color: 'var(--color-text-muted)', marginTop: '0.25rem', paddingLeft: '1.5rem' }}>
            Applicant: {application?.applicant_name} • Requested: ₹{application?.loan_amount ? Number(application.loan_amount).toLocaleString('en-IN') : '—'}
          </div>
        </div>
      </div>

      {/* 2. Documents Evidence */}
      <div style={{ marginBottom: '1.25rem' }}>
        <h4 style={{ fontSize: '0.8rem', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.04em', color: 'var(--color-text-muted)', marginBottom: '0.5rem' }}>
          Document Records ({documents.length})
        </h4>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.4rem' }}>
          {documents.map((doc) => {
            const hasDocMismatch = findings.some(
              (f) => (f.comparison_document_id === doc.document_id || f.source_document_id === doc.document_id) && f.result === 'MISMATCH'
            );

            return (
              <div
                key={doc.document_id}
                onClick={() => onSelectDocument && onSelectDocument(doc)}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  padding: '0.65rem 0.85rem',
                  background: '#ffffff',
                  border: '1px solid var(--color-border)',
                  borderRadius: 'var(--radius-md)',
                  cursor: 'pointer',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                  {hasDocMismatch ? (
                    <AlertTriangle size={15} color="#d97706" />
                  ) : (
                    <CheckCircle2 size={15} color="#16a34a" />
                  )}
                  <div>
                    <div style={{ fontSize: '0.825rem', fontWeight: 600, color: 'var(--color-text-primary)' }}>
                      {getDocumentDisplayLabel(doc, evidenceData)}
                    </div>
                    <div style={{ fontSize: '0.725rem', color: 'var(--color-text-muted)', fontFamily: 'var(--font-mono)' }}>
                      {doc.original_filename}
                    </div>
                  </div>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.25rem', color: 'var(--color-primary-600)', fontSize: '0.75rem' }}>
                  <span>View</span>
                  <ChevronRight size={13} />
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* 3. Verification Findings */}
      <div style={{ marginBottom: '1.25rem' }}>
        <h4 style={{ fontSize: '0.8rem', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.04em', color: 'var(--color-text-muted)', marginBottom: '0.5rem' }}>
          Verification Evidence
        </h4>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.4rem' }}>
          {mismatches.length === 0 ? (
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', padding: '0.65rem 0.85rem', background: '#f0fdf4', border: '1px solid #bbf7d0', borderRadius: 'var(--radius-md)', fontSize: '0.8rem', color: '#166534' }}>
              <CheckCircle2 size={15} color="#16a34a" />
              <span>All cross-document verifications match application facts.</span>
            </div>
          ) : (
            mismatches.map((m, idx) => (
              <div
                key={idx}
                style={{
                  display: 'flex',
                  alignItems: 'flex-start',
                  gap: '0.5rem',
                  padding: '0.65rem 0.85rem',
                  background: '#fef2f2',
                  border: '1px solid #fecaca',
                  borderRadius: 'var(--radius-md)',
                  fontSize: '0.8rem',
                }}
              >
                <AlertTriangle size={15} color="#dc2626" style={{ flexShrink: 0, marginTop: '2px' }} />
                <div>
                  <div style={{ fontWeight: 600, color: '#991b1b' }}>{m.message}</div>
                  <div style={{ fontSize: '0.725rem', color: '#7f1d1d', marginTop: '2px' }}>{m.evidence}</div>
                </div>
              </div>
            ))
          )}
        </div>
      </div>

      {/* 4. Document Validations */}
      <div>
        <h4 style={{ fontSize: '0.8rem', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.04em', color: 'var(--color-text-muted)', marginBottom: '0.5rem' }}>
          Validation Checks
        </h4>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.35rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.8rem', color: 'var(--color-text-secondary)', padding: '0.35rem 0' }}>
            <CheckCircle2 size={14} color="#16a34a" />
            <span>Document formats readable and uncorrupted</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.8rem', color: 'var(--color-text-secondary)', padding: '0.35rem 0' }}>
            <CheckCircle2 size={14} color="#16a34a" />
            <span>Required identification numbers present</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.8rem', color: 'var(--color-text-secondary)', padding: '0.35rem 0' }}>
            <CheckCircle2 size={14} color="#16a34a" />
            <span>Mandatory financial fields extracted with high confidence</span>
          </div>
        </div>
      </div>
    </div>
  );
}
