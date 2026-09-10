import React, { useState } from 'react';
import { Landmark, Building2, Search, BookOpen, ExternalLink, ShieldCheck } from 'lucide-react';
import { api } from '../../services/api';
import { LoadingState } from '../Common/LoadingState';
import { ErrorAlert } from '../Common/ErrorAlert';

export function PolicyTab({ agentReview }) {
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState(null);
  const [searching, setSearching] = useState(false);
  const [searchError, setSearchError] = useState(null);

  const policyReferences = agentReview?.final_review?.policy_references || [];

  const handleSearch = async (e) => {
    e.preventDefault();
    if (!searchQuery.trim()) return;

    try {
      setSearching(true);
      setSearchError(null);
      const res = await api.searchPolicies(searchQuery.trim(), { topK: 4 });
      setSearchResults(res.results || []);
    } catch (err) {
      setSearchError(err.message);
    } finally {
      setSearching(false);
    }
  };

  const rbiCitations = policyReferences.filter((p) => p.authority === 'RBI');
  const bankCitations = policyReferences.filter((p) => p.authority !== 'RBI');

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
      {/* Live Semantic Policy Search Tool */}
      <div className="card" style={{ padding: '1.25rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.5rem' }}>
          <Search size={18} color="var(--color-primary-600)" />
          <h4 style={{ fontSize: '0.95rem', fontWeight: 600 }}>
            Semantic Policy Search (Policy Knowledge Base)
          </h4>
        </div>
        <p style={{ fontSize: '0.8rem', color: 'var(--color-text-secondary)', marginBottom: '0.875rem' }}>
          Query the Policy Knowledge Base to verify RBI regulatory mandates or internal underwriting criteria.
        </p>

        <form onSubmit={handleSearch} style={{ display: 'flex', gap: '0.5rem' }}>
          <input
            type="text"
            className="form-input"
            placeholder="e.g., KYC name mismatch guidelines, minimum income documentation, CIBIL thresholds..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            style={{ flex: 1 }}
          />
          <button type="submit" className="btn btn-primary" disabled={searching}>
            {searching ? 'Retrieving...' : 'Search Policies'}
          </button>
        </form>

        {searchError && <ErrorAlert message={searchError} />}

        {searchResults && (
          <div style={{ marginTop: '1.25rem' }}>
            <h5 style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--color-text-muted)', textTransform: 'uppercase', marginBottom: '0.75rem' }}>
              Search Results ({searchResults.length} matches retrieved from Policy Knowledge Base)
            </h5>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
              {searchResults.map((res, i) => (
                <div key={i} style={{ padding: '0.875rem', background: 'var(--color-bg-subtle)', borderRadius: 'var(--radius-md)', border: '1px solid var(--color-border)' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.35rem' }}>
                    <span className={`badge ${res.authority === 'RBI' ? 'badge-info' : 'badge-neutral'}`} style={{ fontSize: '0.7rem' }}>
                      {res.authority === 'RBI' ? '🏛 RBI REGULATORY' : '🏢 INTERNAL BANK'}
                    </span>
                    <span style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--color-primary-600)' }}>
                      Relevance: {Math.round(res.similarity_score * 100)}%
                    </span>
                  </div>
                  <div style={{ fontWeight: 600, fontSize: '0.875rem', color: 'var(--color-text-primary)', marginBottom: '0.25rem' }}>
                    {res.policy_title} — {res.section_title} ({res.section_id})
                  </div>
                  <p style={{ fontSize: '0.825rem', color: 'var(--color-text-secondary)', lineHeight: 1.4 }}>
                    {res.content}
                  </p>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Citations Grounded in Application Review */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(340px, 1fr))', gap: '1.25rem' }}>
        {/* RBI Regulatory Section */}
        <div className="card">
          <div className="card-header" style={{ borderBottom: '2px solid #0284c7' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <Landmark size={18} color="#0284c7" />
              <div>
                <h4 style={{ fontSize: '0.9rem', fontWeight: 700, color: '#0369a1' }}>
                  🏛 RBI REGULATORY MANDATES
                </h4>
                <span style={{ fontSize: '0.7rem', color: 'var(--color-text-muted)' }}>
                  Legally binding compliance guidelines
                </span>
              </div>
            </div>
            <span className="badge badge-info" style={{ fontSize: '0.7rem' }}>
              {rbiCitations.length} Grounded
            </span>
          </div>

          <div className="card-body">
            {rbiCitations.length > 0 ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.875rem' }}>
                {rbiCitations.map((p, i) => (
                  <div key={i} style={{ padding: '0.875rem', background: 'var(--color-info-bg)', border: '1px solid var(--color-info-border)', borderRadius: 'var(--radius-md)' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.25rem' }}>
                      <strong style={{ fontSize: '0.85rem', color: 'var(--color-info-text)' }}>
                        {p.policy_name}
                      </strong>
                      <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.725rem', color: 'var(--color-info-text)', fontWeight: 600 }}>
                        {p.section_id}
                      </span>
                    </div>
                    <p style={{ fontSize: '0.825rem', color: 'var(--color-info-text)', lineHeight: 1.45 }}>
                      "{p.citation_text}"
                    </p>
                  </div>
                ))}
              </div>
            ) : (
              <div style={{ padding: '1.5rem', textAlign: 'center', color: 'var(--color-text-muted)', fontSize: '0.825rem' }}>
                No regulatory RBI citations required for this standard application.
              </div>
            )}
          </div>
        </div>

        {/* Internal Bank Underwriting Section */}
        <div className="card">
          <div className="card-header" style={{ borderBottom: '2px solid #475569' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <Building2 size={18} color="#475569" />
              <div>
                <h4 style={{ fontSize: '0.9rem', fontWeight: 700, color: '#334155' }}>
                  🏢 INTERNAL BANK UNDERWRITING POLICIES
                </h4>
                <span style={{ fontSize: '0.7rem', color: 'var(--color-text-muted)' }}>
                  Bank credit risk & document thresholds
                </span>
              </div>
            </div>
            <span className="badge badge-neutral" style={{ fontSize: '0.7rem' }}>
              {bankCitations.length} Grounded
            </span>
          </div>

          <div className="card-body">
            {bankCitations.length > 0 ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.875rem' }}>
                {bankCitations.map((p, i) => (
                  <div key={i} style={{ padding: '0.875rem', background: 'var(--color-bg-subtle)', border: '1px solid var(--color-border)', borderRadius: 'var(--radius-md)' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.25rem' }}>
                      <strong style={{ fontSize: '0.85rem', color: 'var(--color-text-primary)' }}>
                        {p.policy_name}
                      </strong>
                      <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.725rem', color: 'var(--color-text-muted)', fontWeight: 600 }}>
                        {p.section_id}
                      </span>
                    </div>
                    <p style={{ fontSize: '0.825rem', color: 'var(--color-text-secondary)', lineHeight: 1.45 }}>
                      "{p.citation_text}"
                    </p>
                  </div>
                ))}
              </div>
            ) : (
              <div style={{ padding: '1.5rem', textAlign: 'center', color: 'var(--color-text-muted)', fontSize: '0.825rem' }}>
                No internal underwriting exceptions triggered.
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
