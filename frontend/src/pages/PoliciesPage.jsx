import React, { useEffect, useState } from 'react';
import { Landmark, Building2, Search, ExternalLink, RefreshCw } from 'lucide-react';
import { api } from '../services/api';
import { LoadingState } from '../components/Common/LoadingState';
import { ErrorAlert } from '../components/Common/ErrorAlert';
import { formatPolicySourceLabel } from '../services/formatters';

export function PoliciesPage() {
  const [policies, setPolicies] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [filterAuthority, setFilterAuthority] = useState('ALL');

  // Search
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState(null);
  const [searching, setSearching] = useState(false);

  const loadPolicies = async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await api.listPolicies();
      setPolicies(res || []);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadPolicies();
  }, []);

  const handleSearch = async (e) => {
    e.preventDefault();
    if (!searchQuery.trim()) return;

    try {
      setSearching(true);
      const res = await api.searchPolicies(searchQuery.trim(), { topK: 5 });
      setSearchResults(res.results || []);
    } catch (err) {
      alert(`Search failed: ${err.message}`);
    } finally {
      setSearching(false);
    }
  };

  const filteredPolicies = policies.filter((p) => {
    if (filterAuthority === 'ALL') return true;
    if (filterAuthority === 'RBI') return (p.authority || '').toUpperCase() === 'RBI';
    if (filterAuthority === 'BANK') return (p.authority || '').toUpperCase() !== 'RBI';
    return p.authority === filterAuthority;
  });

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '1rem' }}>
        <div>
          <h1 style={{ fontSize: '1.5rem', fontWeight: 700, color: 'var(--color-text-primary)' }}>
            Policy Knowledge
          </h1>
          <p style={{ fontSize: '0.85rem', color: 'var(--color-text-secondary)', marginTop: '0.2rem' }}>
            Statutory RBI regulatory directives and internal bank underwriting standards
          </p>
        </div>

        <button
          type="button"
          className="btn btn-secondary btn-sm"
          onClick={loadPolicies}
          disabled={loading}
          style={{ display: 'inline-flex', alignItems: 'center', gap: '0.35rem' }}
        >
          <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
          <span>Refresh</span>
        </button>
      </div>

      {error && <ErrorAlert message={error} onRetry={loadPolicies} />}

      {/* Search Policies Box */}
      <div className="card" style={{ padding: '1.25rem 1.5rem' }}>
        <form onSubmit={handleSearch} style={{ display: 'flex', gap: '0.5rem' }}>
          <div style={{ position: 'relative', flex: 1 }}>
            <Search
              size={16}
              style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)', color: 'var(--color-text-muted)' }}
            />
            <input
              type="text"
              className="form-input"
              placeholder="Search bank policies..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              style={{ paddingLeft: '36px', height: '40px' }}
            />
          </div>
          <button type="submit" className="btn btn-primary" disabled={searching} style={{ padding: '0 1.25rem' }}>
            {searching ? 'Searching...' : 'Search'}
          </button>
        </form>

        {searchResults && (
          <div style={{ marginTop: '1.25rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem' }}>
              <span style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--color-text-muted)', textTransform: 'uppercase' }}>
                Search Results ({searchResults.length} matches)
              </span>
              <button
                type="button"
                className="btn btn-sm btn-secondary"
                onClick={() => setSearchResults(null)}
                style={{ fontSize: '0.75rem', padding: '0.2rem 0.5rem' }}
              >
                Clear Results
              </button>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
              {searchResults.map((res, i) => {
                const sourceLabel = formatPolicySourceLabel(res.citation || res);
                const isRBI = sourceLabel === 'RBI';
                const policyName = res.citation?.policy_name || res.policy_title || (isRBI ? 'RBI Master Direction' : `${sourceLabel} Underwriting Standard`);
                const sectionName = res.citation?.section_title || res.section_title || (isRBI ? 'Regulatory Guidelines' : 'Credit Requirement');
                const sectionRef = res.citation?.section_reference || res.citation?.section_id;

                return (
                  <div
                    key={i}
                    style={{
                      padding: '1rem',
                      background: isRBI ? '#f0f9ff' : '#f8fafc',
                      borderRadius: 'var(--radius-md)',
                      border: isRBI ? '1px solid #bae6fd' : '1px solid var(--color-border)',
                      borderLeft: isRBI ? '4px solid #0284c7' : '4px solid #475569',
                    }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.35rem' }}>
                      <span className={`badge ${isRBI ? 'badge-info' : 'badge-neutral'}`} style={{ fontSize: '0.725rem' }}>
                        {isRBI ? '🏛 RBI' : `🏢 ${sourceLabel}`}
                      </span>
                      {res.similarity_score !== undefined && (
                        <span style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--color-text-muted)' }}>
                          Match: {Math.round(res.similarity_score * 100)}%
                        </span>
                      )}
                    </div>

                    <div style={{ fontWeight: 700, fontSize: '0.9rem', color: 'var(--color-text-primary)', marginBottom: '0.35rem' }}>
                      {policyName} — {sectionName} {sectionRef ? `(${sectionRef})` : ''}
                    </div>

                    <p style={{ fontSize: '0.825rem', color: 'var(--color-text-secondary)', lineHeight: 1.45 }}>
                      {res.content}
                    </p>
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </div>

      {/* Simple Category Filters */}
      <div style={{ display: 'flex', gap: '0.4rem' }}>
        {[
          { id: 'ALL', label: 'All' },
          { id: 'RBI', label: '🏛 RBI Directives' },
          { id: 'BANK', label: '🏢 Bank Policies' },
        ].map((btn) => (
          <button
            key={btn.id}
            type="button"
            className={`btn btn-sm ${filterAuthority === btn.id ? 'btn-primary' : 'btn-secondary'}`}
            onClick={() => setFilterAuthority(btn.id)}
            style={{ borderRadius: 'var(--radius-full)', padding: '0.25rem 0.85rem' }}
          >
            {btn.label}
          </button>
        ))}
      </div>

      {/* Policies Grid */}
      {loading ? (
        <LoadingState message="Loading policy knowledge..." />
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '1rem' }}>
          {filteredPolicies.map((pol) => {
            const sourceLabel = formatPolicySourceLabel(pol);
            const isRBI = sourceLabel === 'RBI';
            return (
              <div
                key={pol.policy_doc_id}
                className="card"
                style={{
                  borderTop: isRBI ? '4px solid #0284c7' : '4px solid #475569',
                  padding: '1.25rem',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
                  <span className={`badge ${isRBI ? 'badge-info' : 'badge-neutral'}`} style={{ fontSize: '0.7rem' }}>
                    {isRBI ? '🏛 RBI' : `🏢 ${sourceLabel}`}
                  </span>
                  <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.725rem', color: 'var(--color-text-muted)' }}>
                    {pol.reference_code || pol.policy_doc_id}
                  </span>
                </div>

                <h3 style={{ fontSize: '0.95rem', fontWeight: 600, color: 'var(--color-text-primary)', marginBottom: '0.35rem' }}>
                  {pol.title}
                </h3>

                <p style={{ fontSize: '0.825rem', color: 'var(--color-text-secondary)', marginBottom: '0.875rem', lineHeight: 1.4 }}>
                  {pol.description}
                </p>

                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '0.75rem', color: 'var(--color-text-muted)', borderTop: '1px solid var(--color-border)', paddingTop: '0.75rem' }}>
                  <span>{pol.section_count} Sections • {pol.rule_count} Rules</span>
                  {pol.official_url && (
                    <a
                      href={pol.official_url}
                      target="_blank"
                      rel="noreferrer"
                      style={{ display: 'inline-flex', alignItems: 'center', gap: '0.25rem', color: 'var(--color-primary-600)' }}
                    >
                      <span>Official Source</span>
                      <ExternalLink size={12} />
                    </a>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

