import React, { useState, useEffect, useRef } from 'react';
import { NavLink, useNavigate } from 'react-router-dom';
import {
  Search,
  Bell,
  ChevronDown,
  Building2,
  Database,
  Sparkles,
  Check,
  LogOut,
  User,
} from 'lucide-react';
import { api } from '../../services/api';
import { useAuth } from '../../context/AuthContext';

export function getInitials(name) {
  if (!name || typeof name !== 'string') return 'U';
  const parts = name.trim().split(/\s+/);
  if (parts.length === 1) {
    return parts[0].substring(0, 2).toUpperCase();
  }
  return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
}

export function formatUserRole(role) {
  if (!role) return 'User';
  if (role === 'LOAN_OFFICER') return 'Loan Officer';
  if (role === 'CUSTOMER') return 'Customer';
  return role
    .toLowerCase()
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

export function TopBar() {
  const { user, logout } = useAuth();
  const [searchQuery, setSearchQuery] = useState('');
  const [seeding, setSeeding] = useState(false);
  const [seedSuccess, setSeedSuccess] = useState(false);
  const [pendingCount, setPendingCount] = useState(0);
  const [profileDropdownOpen, setProfileDropdownOpen] = useState(false);
  const dropdownRef = useRef(null);
  const navigate = useNavigate();

  useEffect(() => {
    function handleClickOutside(event) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setProfileDropdownOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

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

        {/* User Profile Pill & Dropdown */}
        <div className="genbank-profile-container" ref={dropdownRef} style={{ position: 'relative' }}>
          <button
            type="button"
            className="genbank-officer-profile"
            onClick={() => setProfileDropdownOpen((prev) => !prev)}
            aria-expanded={profileDropdownOpen}
            aria-haspopup="true"
            style={{ background: 'none', border: 'none', cursor: 'pointer', textAlign: 'left', padding: '4px 8px', borderRadius: '8px' }}
          >
            {user?.picture_url ? (
              <img
                src={user.picture_url}
                alt={user.name || 'User avatar'}
                className="genbank-officer-avatar"
                style={{ width: '32px', height: '32px', borderRadius: '50%', objectFit: 'cover' }}
              />
            ) : (
              <div className="genbank-officer-avatar">
                {getInitials(user?.name)}
              </div>
            )}
            <div className="genbank-officer-meta">
              <div className="genbank-officer-name">{user?.name || 'Authenticated User'}</div>
              <div className="genbank-officer-role">{formatUserRole(user?.role)}</div>
            </div>
            <ChevronDown
              size={15}
              color="#64748b"
              style={{
                transform: profileDropdownOpen ? 'rotate(180deg)' : 'none',
                transition: 'transform 0.2s',
              }}
            />
          </button>

          {profileDropdownOpen && (
            <div
              className="genbank-profile-dropdown"
              style={{
                position: 'absolute',
                top: 'calc(100% + 6px)',
                right: 0,
                width: '240px',
                backgroundColor: '#ffffff',
                borderRadius: '8px',
                boxShadow: '0 10px 15px -3px rgba(0,0,0,0.1), 0 4px 6px -2px rgba(0,0,0,0.05)',
                border: '1px solid #e2e8f0',
                padding: '0.75rem 0',
                zIndex: 100,
              }}
            >
              <div style={{ padding: '0.5rem 1rem 0.75rem 1rem', borderBottom: '1px solid #f1f5f9' }}>
                <div style={{ fontWeight: 600, fontSize: '0.875rem', color: '#0f172a' }}>
                  {user?.name || 'User'}
                </div>
                <div style={{ fontSize: '0.75rem', color: '#64748b', wordBreak: 'break-all', marginTop: '2px' }}>
                  {user?.email || '—'}
                </div>
                <div style={{ marginTop: '6px' }}>
                  <span
                    style={{
                      display: 'inline-block',
                      fontSize: '0.7rem',
                      fontWeight: 600,
                      padding: '2px 6px',
                      borderRadius: '4px',
                      backgroundColor: user?.role === 'LOAN_OFFICER' ? '#eff6ff' : '#f0fdf4',
                      color: user?.role === 'LOAN_OFFICER' ? '#1e3a8a' : '#166534',
                      border: user?.role === 'LOAN_OFFICER' ? '1px solid #bfdbfe' : '1px solid #bbf7d0',
                    }}
                  >
                    {formatUserRole(user?.role)}
                  </span>
                </div>
              </div>

              <div style={{ padding: '0.25rem 0' }}>
                <button
                  type="button"
                  onClick={handleLogout}
                  style={{
                    width: '100%',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '0.5rem',
                    padding: '0.6rem 1rem',
                    background: 'none',
                    border: 'none',
                    cursor: 'pointer',
                    fontSize: '0.825rem',
                    color: '#dc2626',
                    fontWeight: 500,
                    textAlign: 'left',
                  }}
                  onMouseEnter={(e) => (e.currentTarget.style.backgroundColor = '#fef2f2')}
                  onMouseLeave={(e) => (e.currentTarget.style.backgroundColor = 'transparent')}
                >
                  <LogOut size={15} />
                  <span>Sign Out</span>
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}
