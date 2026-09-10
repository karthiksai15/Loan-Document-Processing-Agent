import React, { useState, useEffect } from 'react';
import { FileText, Download, CheckCircle, AlertTriangle, Eye, ShieldAlert } from 'lucide-react';
import { api } from '../../services/api';
import { StatusBadge } from '../Common/Badges';
import { maskDocumentText } from '../../services/masking';
import { LoadingState } from '../Common/LoadingState';

export function DocumentsTab({ applicationId, documents = [] }) {
  const [selectedDocId, setSelectedDocId] = useState(documents[0]?.document_id || null);
  const [docText, setDocText] = useState('');
  const [docFields, setDocFields] = useState([]);
  const [docValidation, setDocValidation] = useState(null);
  const [loadingDetail, setLoadingDetail] = useState(false);

  useEffect(() => {
    if (documents.length > 0 && !selectedDocId) {
      setSelectedDocId(documents[0].document_id);
    }
  }, [documents, selectedDocId]);

  useEffect(() => {
    if (!selectedDocId) return;

    let isMounted = true;
    async function loadDocDetails() {
      try {
        setLoadingDetail(true);
        const [textRes, fieldsRes, valRes] = await Promise.allSettled([
          api.getDocumentText(selectedDocId),
          api.getDocumentFields(selectedDocId),
          api.getDocumentValidation(selectedDocId),
        ]);

        if (!isMounted) return;

        if (textRes.status === 'fulfilled') {
          setDocText(textRes.value?.extracted_text || '');
        } else {
          setDocText('Text extraction not yet performed or unavailable.');
        }

        if (fieldsRes.status === 'fulfilled') {
          setDocFields(fieldsRes.value?.fields || []);
        } else {
          setDocFields([]);
        }

        if (valRes.status === 'fulfilled') {
          setDocValidation(valRes.value);
        } else {
          setDocValidation(null);
        }
      } finally {
        if (isMounted) setLoadingDetail(false);
      }
    }

    loadDocDetails();
    return () => {
      isMounted = false;
    };
  }, [selectedDocId]);

  const selectedDoc = documents.find((d) => d.document_id === selectedDocId);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
      {/* Document Selector Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '0.875rem' }}>
        {documents.map((doc) => {
          const isSelected = doc.document_id === selectedDocId;
          return (
            <div
              key={doc.document_id}
              className="card"
              onClick={() => setSelectedDocId(doc.document_id)}
              style={{
                padding: '1rem',
                cursor: 'pointer',
                borderColor: isSelected ? 'var(--color-primary-600)' : 'var(--color-border)',
                boxShadow: isSelected ? '0 0 0 2px var(--color-primary-600)' : undefined,
                transition: 'all 0.15s ease',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
                <span className="badge badge-info" style={{ fontSize: '0.7rem' }}>
                  {doc.document_type || 'DOCUMENT'}
                </span>
                <StatusBadge status={doc.processing_status} />
              </div>
              <div style={{ fontWeight: 600, fontSize: '0.875rem', color: 'var(--color-text-primary)', marginBottom: '0.25rem', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                {doc.original_filename}
              </div>
              <div style={{ fontSize: '0.75rem', color: 'var(--color-text-muted)' }}>
                {(doc.file_size / 1024).toFixed(1)} KB • ID: {doc.document_id.slice(-8)}
              </div>
            </div>
          );
        })}
      </div>

      {/* Selected Document Details Workspace */}
      {selectedDoc ? (
        <div className="card">
          <div className="card-header">
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
              <FileText size={18} color="var(--color-primary-600)" />
              <div>
                <h4 style={{ fontSize: '0.95rem', fontWeight: 600 }}>
                  {selectedDoc.original_filename}
                </h4>
                <span style={{ fontSize: '0.75rem', color: 'var(--color-text-muted)' }}>
                  Type: {selectedDoc.document_type} • ID: {selectedDoc.document_id}
                </span>
              </div>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <a
                href={api.getDocumentDownloadUrl(selectedDoc.document_id)}
                target="_blank"
                rel="noreferrer"
                className="btn btn-secondary btn-sm"
                style={{ display: 'inline-flex', alignItems: 'center', gap: '0.35rem' }}
              >
                <Download size={14} />
                <span>Download File</span>
              </a>
            </div>
          </div>

          <div className="card-body">
            {loadingDetail ? (
              <LoadingState message="Loading extracted text & validation rules..." />
            ) : (
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(340px, 1fr))', gap: '1.25rem' }}>
                {/* Left: Document Text with PII Masking */}
                <div>
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
                    <h5 style={{ fontSize: '0.85rem', fontWeight: 600, textTransform: 'uppercase', color: 'var(--color-text-muted)' }}>
                      Extracted Text Content
                    </h5>
                    <span style={{ fontSize: '0.7rem', color: '#15803d', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
                      <ShieldAlert size={12} />
                      <span>PII Protected (Masked)</span>
                    </span>
                  </div>
                  <pre
                    style={{
                      background: 'var(--color-bg-subtle)',
                      padding: '1rem',
                      borderRadius: 'var(--radius-md)',
                      border: '1px solid var(--color-border)',
                      maxHeight: '360px',
                      overflowY: 'auto',
                      whiteSpace: 'pre-wrap',
                      wordBreak: 'break-word',
                      fontSize: '0.8rem',
                      color: 'var(--color-text-primary)',
                      lineHeight: 1.5,
                    }}
                  >
                    {maskDocumentText(docText)}
                  </pre>
                </div>

                {/* Right: Extracted Structured Fields */}
                <div>
                  <h5 style={{ fontSize: '0.85rem', fontWeight: 600, textTransform: 'uppercase', color: 'var(--color-text-muted)', marginBottom: '0.5rem' }}>
                    Extracted Structured Information ({docFields.length} fields)
                  </h5>

                  {docFields.length > 0 ? (
                    <div className="table-wrapper" style={{ maxHeight: '360px', overflowY: 'auto' }}>
                      <table className="data-table">
                        <thead>
                          <tr>
                            <th>Field</th>
                            <th>Value</th>
                            <th>Confidence</th>
                          </tr>
                        </thead>
                        <tbody>
                          {docFields.map((f, i) => (
                            <tr key={i}>
                              <td style={{ fontWeight: 500, fontSize: '0.8rem' }}>
                                {f.field_name.replace(/_/g, ' ')}
                              </td>
                              <td style={{ fontSize: '0.825rem', fontFamily: 'var(--font-mono)' }}>
                                {maskDocumentText(f.normalized_value || f.raw_value) || '—'}
                              </td>
                              <td>
                                <span style={{ fontSize: '0.75rem', fontWeight: 600, color: f.confidence >= 0.9 ? '#15803d' : '#b45309' }}>
                                  {Math.round(f.confidence * 100)}%
                                </span>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  ) : (
                    <div style={{ padding: '2rem', textAlign: 'center', color: 'var(--color-text-muted)', fontSize: '0.825rem', background: 'var(--color-bg-subtle)', borderRadius: 'var(--radius-md)' }}>
                      No structured fields extracted for this document.
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Validation Rules Section */}
            {docValidation && docValidation.checks && (
              <div style={{ marginTop: '1.5rem', paddingTop: '1.25rem', borderTop: '1px solid var(--color-border)' }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.75rem' }}>
                  <h5 style={{ fontSize: '0.85rem', fontWeight: 600, textTransform: 'uppercase', color: 'var(--color-text-muted)' }}>
                    Deterministic Validation Rules ({docValidation.passed_checks}/{docValidation.total_checks} Passed)
                  </h5>
                  <StatusBadge status={docValidation.overall_result} />
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '0.75rem' }}>
                  {docValidation.checks.map((check, idx) => {
                    const isPass = check.status === 'PASS';
                    return (
                      <div
                        key={idx}
                        style={{
                          padding: '0.75rem',
                          borderRadius: 'var(--radius-md)',
                          border: `1px solid ${isPass ? 'var(--color-success-border)' : 'var(--color-warning-border)'}`,
                          backgroundColor: isPass ? 'var(--color-success-bg)' : 'var(--color-warning-bg)',
                          fontSize: '0.8rem',
                        }}
                      >
                        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.25rem' }}>
                          <strong style={{ color: isPass ? 'var(--color-success-text)' : 'var(--color-warning-text)' }}>
                            {check.check_name.replace(/_/g, ' ')}
                          </strong>
                          <span style={{ fontSize: '0.7rem', fontWeight: 700, color: isPass ? 'var(--color-success-text)' : 'var(--color-warning-text)' }}>
                            {check.status}
                          </span>
                        </div>
                        <div style={{ color: isPass ? 'var(--color-success-text)' : 'var(--color-warning-text)', opacity: 0.9 }}>
                          {check.message}
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}
          </div>
        </div>
      ) : (
        <div className="card" style={{ padding: '2rem', textAlign: 'center', color: 'var(--color-text-muted)' }}>
          No documents uploaded for this application.
        </div>
      )}
    </div>
  );
}
