import React, { useState } from 'react';
import { Share2, FileText, CheckCircle, AlertTriangle, Filter, Search } from 'lucide-react';
import { maskDocumentText } from '../../services/masking';
import { StatusBadge } from '../Common/Badges';

export function EvidenceGraphTab({ evidenceData, verificationData }) {
  const [filterType, setFilterType] = useState('ALL');
  const [searchTerm, setSearchTerm] = useState('');

  const nodes = evidenceData?.nodes || [];
  const relationships = evidenceData?.relationships || [];
  const findings = verificationData?.findings || [];

  const filteredNodes = nodes.filter((node) => {
    if (filterType !== 'ALL' && node.node_type !== filterType) return false;
    if (searchTerm) {
      const q = searchTerm.toLowerCase();
      return (
        node.title?.toLowerCase().includes(q) ||
        node.value?.toLowerCase().includes(q) ||
        node.node_id?.toLowerCase().includes(q)
      );
    }
    return true;
  });

  const nodeTypes = ['ALL', ...new Set(nodes.map((n) => n.node_type))];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
      {/* Visual Relationship Flow Highlights */}
      <div className="card">
        <div className="card-header">
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <Share2 size={16} color="var(--color-primary-600)" />
            <h4 style={{ fontSize: '0.9rem', fontWeight: 600 }}>Cross-Document Evidence Chain</h4>
          </div>
          <span style={{ fontSize: '0.75rem', color: 'var(--color-text-muted)' }}>
            {findings.length} Verification Comparisons • {relationships.length} Graph Relationships
          </span>
        </div>
        <div className="card-body">
          {findings.length > 0 ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
              {findings.map((f, idx) => (
                <div
                  key={idx}
                  style={{
                    padding: '1rem',
                    borderRadius: 'var(--radius-lg)',
                    border: `1px solid ${f.result === 'MISMATCH' ? 'var(--color-danger-border)' : 'var(--color-border)'}`,
                    backgroundColor: f.result === 'MISMATCH' ? 'var(--color-danger-bg)' : 'var(--color-bg-subtle)',
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.75rem' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                      {f.result === 'MISMATCH' ? (
                        <AlertTriangle size={16} color="var(--color-danger-text)" />
                      ) : (
                        <CheckCircle size={16} color="var(--color-success-text)" />
                      )}
                      <span style={{ fontWeight: 600, fontSize: '0.875rem', color: f.result === 'MISMATCH' ? 'var(--color-danger-text)' : 'var(--color-text-primary)' }}>
                        {f.rule_name}
                      </span>
                    </div>
                    <StatusBadge status={f.result} />
                  </div>

                  {/* Flow Box: Source A -> Compared With -> Source B */}
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', flexWrap: 'wrap' }}>
                    <div style={{ flex: 1, minWidth: '180px', background: '#ffffff', padding: '0.625rem 0.875rem', borderRadius: 'var(--radius-md)', border: '1px solid var(--color-border)' }}>
                      <span style={{ fontSize: '0.7rem', color: 'var(--color-text-muted)', textTransform: 'uppercase', display: 'block' }}>
                        Source A: {f.source_a} ({f.field_a})
                      </span>
                      <strong style={{ fontSize: '0.9rem', color: 'var(--color-text-primary)' }}>
                        {maskDocumentText(f.value_a) || '—'}
                      </strong>
                    </div>

                    <div style={{ fontSize: '0.75rem', color: 'var(--color-text-muted)', fontWeight: 600, textTransform: 'uppercase' }}>
                      ── compared with ──▶
                    </div>

                    <div style={{ flex: 1, minWidth: '180px', background: '#ffffff', padding: '0.625rem 0.875rem', borderRadius: 'var(--radius-md)', border: `1px solid ${f.result === 'MISMATCH' ? 'var(--color-danger-border)' : 'var(--color-border)'}` }}>
                      <span style={{ fontSize: '0.7rem', color: f.result === 'MISMATCH' ? 'var(--color-danger-text)' : 'var(--color-text-muted)', textTransform: 'uppercase', display: 'block' }}>
                        Source B: {f.source_b} ({f.field_b})
                      </span>
                      <strong style={{ fontSize: '0.9rem', color: f.result === 'MISMATCH' ? 'var(--color-danger-text)' : 'var(--color-text-primary)' }}>
                        {maskDocumentText(f.value_b) || '—'}
                      </strong>
                    </div>
                  </div>

                  {f.message && (
                    <div style={{ marginTop: '0.5rem', fontSize: '0.8rem', color: f.result === 'MISMATCH' ? 'var(--color-danger-text)' : 'var(--color-text-secondary)' }}>
                      {f.message}
                    </div>
                  )}
                </div>
              ))}
            </div>
          ) : (
            <div style={{ fontSize: '0.85rem', color: 'var(--color-text-muted)', fontStyle: 'italic' }}>
              No verification findings available yet. Trigger verification from the Actions menu.
            </div>
          )}
        </div>
      </div>

      {/* Filterable Evidence Nodes Table */}
      <div className="card">
        <div className="card-header" style={{ flexWrap: 'wrap', gap: '0.75rem' }}>
          <div>
            <h4 style={{ fontSize: '0.9rem', fontWeight: 600 }}>Evidence Graph Nodes</h4>
            <span style={{ fontSize: '0.75rem', color: 'var(--color-text-muted)' }}>
              Total grounded nodes: {nodes.length} (showing {filteredNodes.length})
            </span>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            {/* Search Filter */}
            <div style={{ position: 'relative' }}>
              <Search size={14} style={{ position: 'absolute', left: '8px', top: '50%', transform: 'translateY(-50%)', color: 'var(--color-text-muted)' }} />
              <input
                type="text"
                className="form-input"
                placeholder="Search nodes..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                style={{ paddingLeft: '28px', height: '32px', fontSize: '0.775rem', width: '160px' }}
              />
            </div>

            {/* Type Filter */}
            <select
              className="form-select"
              value={filterType}
              onChange={(e) => setFilterType(e.target.value)}
              style={{ height: '32px', fontSize: '0.775rem', width: '150px' }}
            >
              {nodeTypes.map((t) => (
                <option key={t} value={t}>
                  {t === 'ALL' ? 'All Types' : t.replace(/_/g, ' ')}
                </option>
              ))}
            </select>
          </div>
        </div>

        <div className="table-wrapper" style={{ border: 'none', borderRadius: 0 }}>
          <table className="data-table">
            <thead>
              <tr>
                <th>Node ID</th>
                <th>Type</th>
                <th>Title / Label</th>
                <th>Value (Masked)</th>
                <th>Confidence</th>
                <th>Source Reference</th>
              </tr>
            </thead>
            <tbody>
              {filteredNodes.length > 0 ? (
                filteredNodes.map((node) => (
                  <tr key={node.node_id}>
                    <td style={{ fontFamily: 'var(--font-mono)', fontSize: '0.75rem', color: 'var(--color-primary-700)' }}>
                      {node.node_id}
                    </td>
                    <td>
                      <span className="badge badge-neutral" style={{ fontSize: '0.675rem' }}>
                        {node.node_type}
                      </span>
                    </td>
                    <td style={{ fontWeight: 500 }}>
                      {node.title}
                    </td>
                    <td style={{ maxWidth: '240px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {maskDocumentText(node.value) || '—'}
                    </td>
                    <td>
                      <span style={{ fontSize: '0.8rem', fontWeight: 600, color: node.confidence >= 0.9 ? '#15803d' : '#b45309' }}>
                        {Math.round(node.confidence * 100)}%
                      </span>
                    </td>
                    <td style={{ fontSize: '0.775rem', color: 'var(--color-text-muted)' }}>
                      {node.source_reference || node.source_type || 'SYSTEM'}
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={6} style={{ textAlign: 'center', color: 'var(--color-text-muted)', padding: '2rem' }}>
                    No evidence nodes match your filter.
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
