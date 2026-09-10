import React, { useState, useEffect } from 'react';
import { NavLink, useNavigate } from 'react-router-dom';
import {
  Search,
  Bell,
  ChevronDown,
  Building2,
  Database,
  Sparkles,
  Check,
} from 'lucide-react';
import { api } from '../../services/api';

export function TopBar() {
  const [searchQuery, setSearchQuery] = useState('');
  const [seeding, setSeeding] = useState(false);
  const [seedSuccess, setSeedSuccess] = useState(false);
  const [pendingCount, setPendingCount] = useState(0);
  const navigate = useNavigate();

  const fetchPending = async () => {
    try {
      const data = await api.getDashboardOverview();
      setPendingCount(data.review_required_count || 0);
    } catch {
      // ignore in header
    }
  };

  useEffect(() => {
    fetchPending();
    const handleSeeded = () => fetchPending();
    window.addEventListener('loan-data-seeded', handleSeeded);
    return () => window.removeEventListener('loan-data-seeded', handleSeeded);
  }, []);

  const handleSearch = (e) => {
    e.preventDefault();
    const clean = searchQuery.trim().toUpperCase();
    if (clean) {
      if (clean.startsWith('A0') || clean.startsWith('APP-')) {
        navigate(`/applications/${clean}`);
      } else {
        navigate(`/applications?search=${encodeURIComponent(clean)}`);
      }
      setSearchQuery('');
    }
  };

  const handleSeedData = async () => {
    try {
      setSeeding(true);
      await api.seedDemoData();
      setSeedSuccess(true);
      setTimeout(() => setSeedSuccess(false), 4000);
      window.dispatchEvent(new CustomEvent('loan-data-seeded'));
      fetchPending();
    } catch (err) {
      alert(`Loading demo data failed: ${err.message}`);
    } finally {
      setSeeding(false);
    }
  };

  return (
    <header className="genbank-topbar">
      {/* Brand & Main Nav Links */}
      <div className="genbank-topbar-left">
        <div className="genbank-brand" onClick={() => navigate('/dashboard')}>
          <div className="genbank-logo-icon">
            <Building2 size={20} color="#ffffff" />
          </div>
          <span className="genbank-brand-name">GenBank</span>
        </div>

        <nav className="genbank-nav-tabs">
          <NavLink
            to="/dashboard"
            className={({ isActive }) => `genbank-nav-tab ${isActive ? 'active' : ''}`}
          >
            Dashboard
          </NavLink>
          <NavLink
            to="/applications"
            className={({ isActive }) => `genbank-nav-tab ${isActive ? 'active' : ''}`}
          >
            Applications
          </NavLink>
        </nav>
      </div>

      {/* Global Search Input */}
      <div className="genbank-topbar-center">
        <form onSubmit={handleSearch} className="genbank-search-form">
          <Search size={16} className="genbank-search-icon" />
          <input
            type="text"
            className="genbank-search-input"
            placeholder="Search applications, documents, or applicants..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
        </form>
      </div>

      {/* Actions, Notifications & Officer Profile */}
      <div className="genbank-topbar-right">
        {/* Demo Data Loader Tool */}
        <button
          type="button"
          className="btn btn-secondary btn-sm"
          onClick={handleSeedData}
          disabled={seeding}
          title="Load demo applications A001–A010"
          style={{ height: '34px', fontSize: '0.75rem', padding: '0 0.65rem' }}
        >
          {seeding ? (
            <>
              <Sparkles size={13} className="animate-spin" />
              <span>Loading Demo Data...</span>
            </>
          ) : seedSuccess ? (
            <>
              <Check size={13} color="#15803d" />
              <span style={{ color: '#15803d', fontWeight: 600 }}>Demo Data Loaded</span>
            </>
          ) : (
            <>
              <Database size={13} />
              <span>Load Demo Data</span>
            </>
          )}
        </button>

        {/* Notifications Icon with Badge */}
        <div className="genbank-bell-wrap" title={pendingCount > 0 ? `${pendingCount} applications require review` : "No pending alerts"}>
          <Bell size={19} color="#475569" />
          {pendingCount > 0 && <span className="genbank-bell-badge">{pendingCount}</span>}
        </div>

        {/* Loan Officer Profile Pill */}
        <div className="genbank-officer-profile">
          <div className="genbank-officer-avatar">PS</div>
          <div className="genbank-officer-meta">
            <div className="genbank-officer-name">Priya Sharma</div>
            <div className="genbank-officer-role">Loan Officer</div>
          </div>
          <ChevronDown size={15} color="#64748b" />
        </div>
      </div>
    </header>
  );
}
