import React, { useState, useRef, useEffect } from 'react';
import { NavLink, useNavigate } from 'react-router-dom';
import { Building2, PlusCircle, FileText, LogOut, User, ChevronDown } from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import { getInitials } from '../Layout/TopBar';

export function CustomerTopBar() {
  const { user, logout } = useAuth();
  const [profileOpen, setProfileOpen] = useState(false);
  const dropdownRef = useRef(null);
  const navigate = useNavigate();

  useEffect(() => {
    function handleClickOutside(event) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setProfileOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const displayName = user?.name || user?.email || 'Applicant';
  const displayEmail = user?.email || '';
  const initials = getInitials(displayName);

  return (
    <header className="customer-topbar">
      <div className="customer-topbar-left">
        <NavLink to="/customer/dashboard" className="customer-brand">
          <div className="customer-logo-badge">
            <Building2 size={20} color="#ffffff" />
          </div>
          <div className="customer-brand-text">
            <span className="customer-brand-name">GenBank</span>
            <span className="customer-portal-tag">Customer Portal</span>
          </div>
        </NavLink>

        <nav className="customer-nav">
          <NavLink
            to="/customer/dashboard"
            end
            className={({ isActive }) =>
              isActive ? 'customer-nav-link active' : 'customer-nav-link'
            }
          >
            <FileText size={16} />
            My Applications
          </NavLink>
          <NavLink
            to="/customer/applications/new"
            className={({ isActive }) =>
              isActive ? 'customer-nav-link active' : 'customer-nav-link'
            }
          >
            <PlusCircle size={16} />
            New Application
          </NavLink>
        </nav>
      </div>

      <div className="customer-topbar-right">
        <div className="customer-user-wrapper" ref={dropdownRef}>
          <button
            type="button"
            className="customer-user-btn"
            onClick={() => setProfileOpen((prev) => !prev)}
            aria-expanded={profileOpen}
          >
            <div className="customer-user-avatar">
              {user?.picture_url ? (
                <img
                  src={user.picture_url}
                  alt={displayName}
                  className="customer-avatar-img"
                  referrerPolicy="no-referrer"
                />
              ) : (
                <span>{initials}</span>
              )}
            </div>
            <div className="customer-user-info">
              <span className="customer-user-name">{displayName}</span>
              <span className="customer-user-role">Applicant</span>
            </div>
            <ChevronDown size={14} className="customer-dropdown-icon" />
          </button>

          {profileOpen && (
            <div className="customer-profile-menu">
              <div className="customer-profile-header">
                <span className="profile-full-name">{displayName}</span>
                {displayEmail && <span className="profile-email">{displayEmail}</span>}
                <span className="profile-role-pill">Verified Applicant</span>
              </div>
              <div className="profile-menu-divider" />
              <button
                type="button"
                className="profile-logout-item"
                onClick={handleLogout}
              >
                <LogOut size={15} />
                <span>Sign Out</span>
              </button>
            </div>
          )}
        </div>
      </div>

      <style>{`
        .customer-topbar {
          height: 64px;
          background: #ffffff;
          border-bottom: 1px solid #e2e8f0;
          display: flex;
          align-items: center;
          justify-content: space-between;
          padding: 0 1.5rem;
          position: sticky;
          top: 0;
          z-index: 40;
          box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
        }

        .customer-topbar-left {
          display: flex;
          align-items: center;
          gap: 2rem;
        }

        .customer-brand {
          display: flex;
          align-items: center;
          gap: 0.75rem;
          text-decoration: none;
        }

        .customer-logo-badge {
          width: 36px;
          height: 36px;
          background: linear-gradient(135deg, #1e3a8a 0%, #2563eb 100%);
          border-radius: 8px;
          display: flex;
          align-items: center;
          justify-content: center;
          box-shadow: 0 2px 4px rgba(37, 99, 235, 0.2);
        }

        .customer-brand-text {
          display: flex;
          flex-direction: column;
        }

        .customer-brand-name {
          font-size: 1.125rem;
          font-weight: 700;
          color: #0f172a;
          line-height: 1.2;
          letter-spacing: -0.02em;
        }

        .customer-portal-tag {
          font-size: 0.6875rem;
          font-weight: 600;
          color: #2563eb;
          text-transform: uppercase;
          letter-spacing: 0.05em;
        }

        .customer-nav {
          display: flex;
          align-items: center;
          gap: 0.5rem;
        }

        .customer-nav-link {
          display: flex;
          align-items: center;
          gap: 0.375rem;
          padding: 0.5rem 0.875rem;
          border-radius: 6px;
          font-size: 0.875rem;
          font-weight: 500;
          color: #64748b;
          text-decoration: none;
          transition: all 0.15s ease;
        }

        .customer-nav-link:hover {
          color: #0f172a;
          background: #f1f5f9;
        }

        .customer-nav-link.active {
          color: #1e3a8a;
          background: #eff6ff;
          font-weight: 600;
        }

        .customer-topbar-right {
          display: flex;
          align-items: center;
          gap: 1rem;
        }

        .customer-user-wrapper {
          position: relative;
        }

        .customer-user-btn {
          display: flex;
          align-items: center;
          gap: 0.75rem;
          background: none;
          border: 1px solid #e2e8f0;
          padding: 0.375rem 0.75rem 0.375rem 0.375rem;
          border-radius: 24px;
          cursor: pointer;
          transition: all 0.15s ease;
        }

        .customer-user-btn:hover {
          background: #f8fafc;
          border-color: #cbd5e1;
        }

        .customer-user-avatar {
          width: 32px;
          height: 32px;
          border-radius: 50%;
          background: #2563eb;
          color: #ffffff;
          display: flex;
          align-items: center;
          justify-content: center;
          font-size: 0.8125rem;
          font-weight: 600;
          overflow: hidden;
        }

        .customer-avatar-img {
          width: 100%;
          height: 100%;
          object-fit: cover;
        }

        .customer-user-info {
          display: flex;
          flex-direction: column;
          align-items: flex-start;
          text-align: left;
        }

        .customer-user-name {
          font-size: 0.8125rem;
          font-weight: 600;
          color: #0f172a;
          line-height: 1.2;
          max-width: 130px;
          white-space: nowrap;
          overflow: hidden;
          text-overflow: ellipsis;
        }

        .customer-user-role {
          font-size: 0.6875rem;
          color: #64748b;
        }

        .customer-dropdown-icon {
          color: #94a3b8;
        }

        .customer-profile-menu {
          position: absolute;
          top: calc(100% + 8px);
          right: 0;
          width: 240px;
          background: #ffffff;
          border-radius: 10px;
          border: 1px solid #e2e8f0;
          box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05);
          padding: 0.75rem 0;
          z-index: 50;
        }

        .customer-profile-header {
          display: flex;
          flex-direction: column;
          padding: 0.5rem 1rem 0.75rem 1rem;
        }

        .profile-full-name {
          font-size: 0.875rem;
          font-weight: 600;
          color: #0f172a;
        }

        .profile-email {
          font-size: 0.75rem;
          color: #64748b;
          margin-top: 0.125rem;
          word-break: break-all;
        }

        .profile-role-pill {
          display: inline-block;
          margin-top: 0.5rem;
          padding: 0.125rem 0.5rem;
          background: #eff6ff;
          color: #1d4ed8;
          border-radius: 12px;
          font-size: 0.6875rem;
          font-weight: 600;
          width: fit-content;
        }

        .profile-menu-divider {
          height: 1px;
          background: #f1f5f9;
          margin: 0.25rem 0;
        }

        .profile-logout-item {
          display: flex;
          align-items: center;
          gap: 0.5rem;
          width: 100%;
          padding: 0.625rem 1rem;
          background: none;
          border: none;
          font-size: 0.8125rem;
          font-weight: 500;
          color: #dc2626;
          cursor: pointer;
          transition: background-color 0.15s ease;
          text-align: left;
        }

        .profile-logout-item:hover {
          background: #fef2f2;
        }
      `}</style>
    </header>
  );
}

export default CustomerTopBar;
