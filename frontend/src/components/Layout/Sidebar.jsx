import React, { useEffect, useState } from 'react';
import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard,
  FileText,
  Settings,
  HelpCircle,
} from 'lucide-react';
import { api } from '../../services/api';

export function Sidebar() {
  const [aiStatus, setAiStatus] = useState({
    status: 'checking',
    label: 'Checking AI...',
    connected: false,
  });

  useEffect(() => {
    let isMounted = true;
    const checkStatus = async () => {
      try {
        const info = await api.getSystemInfo();
        if (!isMounted) return;
        const prov = (info?.active_llm_provider || '').toLowerCase();
        const isAvailable = prov && !prov.includes('unavailable') && !prov.includes('error');
        if (isAvailable) {
          setAiStatus({
            status: 'connected',
            label: 'AI: Ready',
            connected: true,
          });
        } else {
          setAiStatus({
            status: 'degraded',
            label: 'AI: Degraded',
            connected: false,
          });
        }
      } catch {
        if (isMounted) {
          setAiStatus({
            status: 'degraded',
            label: 'AI: Degraded',
            connected: false,
          });
        }
      }
    };

    checkStatus();
    return () => {
      isMounted = false;
    };
  }, []);

  return (
    <aside className="sidebar genbank-sidebar">
      <nav className="sidebar-nav">
        <NavLink
          to="/dashboard"
          className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}
          title="Dashboard"
        >
          <LayoutDashboard size={19} />
          <span>Dashboard</span>
        </NavLink>

        <NavLink
          to="/applications"
          className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}
          title="Applications"
        >
          <FileText size={19} />
          <span>Applications</span>
        </NavLink>

        <NavLink
          to="/settings"
          onClick={(e) => {
            e.preventDefault();
            alert('Settings: Loan Officer Preferences & Underwriting Thresholds are managed per bank guidelines.');
          }}
          className="nav-item"
          title="Settings"
        >
          <Settings size={19} />
          <span>Settings</span>
        </NavLink>
      </nav>

      <div className="sidebar-footer" style={{ borderTop: '1px solid rgba(255, 255, 255, 0.08)', padding: '0.75rem' }}>
        <button
          type="button"
          className="nav-item"
          style={{ width: '100%', background: 'transparent', border: 'none', cursor: 'pointer', textAlign: 'left', padding: '0.4rem 0.5rem', color: '#94a3b8' }}
          onClick={() => alert('GenBank Loan Officer Operations Helpdesk: Extension 4402 | helpdesk@genbank.internal')}
          title="Help & Support"
        >
          <HelpCircle size={18} />
          <span style={{ fontSize: '0.8rem' }}>Help & Support</span>
        </button>

        <div
          style={{
            marginTop: '0.5rem',
            paddingTop: '0.4rem',
            display: 'flex',
            alignItems: 'center',
            gap: '0.4rem',
            fontSize: '0.7rem',
            color: aiStatus.connected ? '#86efac' : '#fcd34d',
          }}
          title={aiStatus.label}
        >
          <span
            style={{
              width: '7px',
              height: '7px',
              borderRadius: '50%',
              background: aiStatus.connected ? '#22c55e' : '#f59e0b',
              flexShrink: 0,
            }}
          />
          <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
            {aiStatus.label}
          </span>
        </div>
      </div>
    </aside>
  );
}
