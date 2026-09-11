import React, { useEffect, useRef, useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { ShieldCheck, User, Briefcase, ArrowRight, ArrowLeft, AlertCircle, Loader2 } from 'lucide-react';
import { useAuth } from '../context/AuthContext';

export function LoginPage() {
  const { user, login, isAuthenticated } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  // Selected portal: null (selection view) | 'CUSTOMER' | 'OFFICER'
  const [selectedPortal, setSelectedPortal] = useState(() => {
    if (typeof window !== 'undefined' && window.sessionStorage) {
      return window.sessionStorage.getItem('genbank_selected_portal') || null;
    }
    return null;
  });
  const selectedPortalRef = useRef(selectedPortal);
  const googleButtonRef = useRef(null);
  const [authLoading, setAuthLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState(null);
  const [scriptLoaded, setScriptLoaded] = useState(false);

  // Sync ref and sessionStorage whenever selectedPortal changes
  useEffect(() => {
    selectedPortalRef.current = selectedPortal;
    if (typeof window !== 'undefined' && window.sessionStorage) {
      if (selectedPortal) {
        window.sessionStorage.setItem('genbank_selected_portal', selectedPortal);
      } else {
        window.sessionStorage.removeItem('genbank_selected_portal');
      }
    }
  }, [selectedPortal]);

  // If already authenticated and not in an active login flow, redirect immediately based on role
  useEffect(() => {
    if (authLoading) return;

    if (isAuthenticated && user) {
      const rawFrom = location.state?.from;
      const fromPath = typeof rawFrom === 'string' ? rawFrom : rawFrom?.pathname;
      const isValidProtectedPath = fromPath && fromPath !== '/' && fromPath !== '/login';

      let dest;
      if (user.role === 'CUSTOMER') {
        dest = isValidProtectedPath && fromPath.startsWith('/customer')
          ? fromPath
          : '/customer/dashboard';
      } else {
        dest = isValidProtectedPath && !fromPath.startsWith('/customer')
          ? fromPath
          : '/dashboard';
      }
      console.log('[AUTH DEBUG] LoginPage useEffect redirect:', { userRole: user.role, dest, fromPath });
      navigate(dest, { replace: true });
    }
  }, [isAuthenticated, user, authLoading, navigate, location]);

  // Load Google Identity Services script if not already present
  useEffect(() => {
    if (window.google?.accounts?.id) {
      setScriptLoaded(true);
      return;
    }

    const existingScript = document.querySelector('script[src="https://accounts.google.com/gsi/client"]');
    if (existingScript) {
      existingScript.addEventListener('load', () => setScriptLoaded(true));
      return;
    }

    const script = document.createElement('script');
    script.src = 'https://accounts.google.com/gsi/client';
    script.async = true;
    script.defer = true;
    script.onload = () => setScriptLoaded(true);
    script.onerror = () => setErrorMessage('Failed to load Google Sign-In SDK. Please check your network connection.');
    document.head.appendChild(script);
  }, []);

  // Initialize and render Google Sign-In button whenever a portal is selected
  useEffect(() => {
    if (!selectedPortal || !scriptLoaded || !googleButtonRef.current || !window.google?.accounts?.id) {
      return;
    }

    const clientId =
      import.meta.env.VITE_GOOGLE_CLIENT_ID ||
      '927480599191-iock07diunjgmr0t3fdi3teh7ot5grk5.apps.googleusercontent.com';

    try {
      window.google.accounts.id.initialize({
        client_id: clientId,
        callback: handleGoogleResponse,
        auto_select: false,
        cancel_on_tap_outside: true,
      });

      // Clear any previous button renderings
      googleButtonRef.current.innerHTML = '';

      window.google.accounts.id.renderButton(googleButtonRef.current, {
        theme: 'outline',
        size: 'large',
        type: 'standard',
        shape: 'rectangular',
        text: 'continue_with',
        logo_alignment: 'left',
        width: 320,
      });
    } catch (err) {
      setErrorMessage('Could not initialize Google Sign-In. Please reload the page.');
    }
  }, [selectedPortal, scriptLoaded]);

  // Handle Google OAuth token response
  const handleGoogleResponse = async (response) => {
    if (!response?.credential) {
      setErrorMessage('Google Sign-In was cancelled or did not return a valid credential.');
      return;
    }

    setAuthLoading(true);
    setErrorMessage(null);

    const savedPortal = typeof window !== 'undefined' && window.sessionStorage
      ? window.sessionStorage.getItem('genbank_selected_portal')
      : null;
    const currentPortal = selectedPortalRef.current || selectedPortal || savedPortal;
    const requestedRole = currentPortal === 'OFFICER' ? 'LOAN_OFFICER' : 'CUSTOMER';

    console.log('[AUTH DEBUG] handleGoogleResponse triggered');
    console.log('[AUTH DEBUG] selectedPortal state:', selectedPortal);
    console.log('[AUTH DEBUG] selectedPortalRef.current:', selectedPortalRef.current);
    console.log('[AUTH DEBUG] currentPortal (resolved):', currentPortal);
    console.log('[AUTH DEBUG] requestedRole:', requestedRole);

    try {
      const result = await login(response.credential, requestedRole);
      const authenticatedUser = result?.user;

      console.log('[AUTH DEBUG] login() response:', result);
      console.log('[AUTH DEBUG] authenticated user object:', authenticatedUser);
      console.log('[AUTH DEBUG] user.role:', authenticatedUser?.role);
      console.log('[AUTH DEBUG] location.state?.from:', location.state?.from);

      const rawFrom = location.state?.from;
      const fromPath = typeof rawFrom === 'string' ? rawFrom : rawFrom?.pathname;
      const isValidProtectedPath = fromPath && fromPath !== '/' && fromPath !== '/login';

      let dest;
      if (authenticatedUser?.role === 'CUSTOMER') {
        dest = isValidProtectedPath && fromPath.startsWith('/customer')
          ? fromPath
          : '/customer/dashboard';
      } else {
        dest = isValidProtectedPath && !fromPath.startsWith('/customer')
          ? fromPath
          : '/dashboard';
      }

      console.log('[AUTH DEBUG] final destination passed to navigate():', dest);
      navigate(dest, { replace: true });
    } catch (err) {
      console.error('[AUTH DEBUG] Authentication failure in handleGoogleResponse:', err);
      setErrorMessage(
        err?.message || 'Failed to authenticate with GenBank server. Please try again.'
      );
    } finally {
      setAuthLoading(false);
    }
  };

  return (
    <div className="login-page-container">
      <div className="login-card">
        {/* GenBank Brand Header */}
        <div className="login-brand-section">
          <div className="login-logo-badge">
            <ShieldCheck size={36} color="#ffffff" />
          </div>
          <h1 className="login-brand-title">GenBank</h1>
          <h2 className="login-app-subtitle">Loan Document Processing Agent</h2>
          <p className="login-description">
            Autonomous Document Intelligence & Human-in-the-Loop Underwriting
          </p>
        </div>

        {/* Divider */}
        <div className="login-divider" />

        {/* Portal Selection View */}
        {!selectedPortal ? (
          <div className="portal-selection-section">
            <p className="portal-selection-intro">
              Select your portal to continue:
            </p>

            <div className="portal-cards-grid">
              {/* Customer Portal Card */}
              <div
                className="portal-choice-card"
                onClick={() => {
                  setErrorMessage(null);
                  setSelectedPortal('CUSTOMER');
                }}
                role="button"
                tabIndex={0}
                onKeyDown={(e) => e.key === 'Enter' && setSelectedPortal('CUSTOMER')}
              >
                <div className="portal-choice-icon-wrap customer-icon">
                  <User size={26} color="#2563eb" />
                </div>
                <div className="portal-choice-info">
                  <h3 className="portal-choice-title">Customer / Applicant</h3>
                  <p className="portal-choice-desc">
                    Apply for a loan and track your application
                  </p>
                </div>
                <button
                  type="button"
                  className="portal-choice-btn btn-customer"
                  onClick={(e) => {
                    e.stopPropagation();
                    setErrorMessage(null);
                    setSelectedPortal('CUSTOMER');
                  }}
                >
                  Continue as Customer <ArrowRight size={16} />
                </button>
              </div>

              {/* Loan Officer / Manager Portal Card */}
              <div
                className="portal-choice-card"
                onClick={() => {
                  setErrorMessage(null);
                  setSelectedPortal('OFFICER');
                }}
                role="button"
                tabIndex={0}
                onKeyDown={(e) => e.key === 'Enter' && setSelectedPortal('OFFICER')}
              >
                <div className="portal-choice-icon-wrap officer-icon">
                  <Briefcase size={26} color="#0f766e" />
                </div>
                <div className="portal-choice-info">
                  <h3 className="portal-choice-title">Loan Officer / Manager</h3>
                  <p className="portal-choice-desc">
                    Review and process customer applications
                  </p>
                </div>
                <button
                  type="button"
                  className="portal-choice-btn btn-officer"
                  onClick={(e) => {
                    e.stopPropagation();
                    setErrorMessage(null);
                    setSelectedPortal('OFFICER');
                  }}
                >
                  Continue as Loan Officer <ArrowRight size={16} />
                </button>
              </div>
            </div>
          </div>
        ) : (
          /* Google Sign-In Step for Selected Portal */
          <div className="login-action-section">
            <button
              type="button"
              className="back-portal-link"
              onClick={() => {
                setSelectedPortal(null);
                setErrorMessage(null);
              }}
            >
              <ArrowLeft size={16} /> Switch Portal
            </button>

            <div className="active-portal-badge">
              {selectedPortal === 'CUSTOMER' ? (
                <>
                  <User size={18} color="#2563eb" />
                  <span>Customer & Applicant Portal</span>
                </>
              ) : (
                <>
                  <Briefcase size={18} color="#0f766e" />
                  <span>Loan Officer & Staff Portal</span>
                </>
              )}
            </div>

            <p className="login-instruction">
              {selectedPortal === 'CUSTOMER'
                ? 'Sign in with your Google account to create loan requests and track real-time underwriting progress.'
                : 'Sign in with your authorized GenBank enterprise Google account to review applications and make credit decisions.'}
            </p>

            {/* Error Banner */}
            {errorMessage && (
              <div className="login-error-banner" role="alert">
                <AlertCircle size={18} className="login-error-icon" />
                <span>{errorMessage}</span>
              </div>
            )}

            {/* Google Sign-In Button Container */}
            <div className="login-button-wrapper">
              {authLoading ? (
                <div className="login-loading-state">
                  <Loader2 size={24} className="login-spinner-icon" />
                  <span>Authenticating with GenBank security...</span>
                </div>
              ) : (
                <div ref={googleButtonRef} className="google-btn-slot" />
              )}
            </div>
          </div>
        )}

        {/* Security Notice Footer */}
        <div className="login-footer">
          <p className="login-security-notice">
            Protected by 256-bit encryption • Authorized Bank Staff & Applicants
          </p>
        </div>
      </div>

      <style>{`
        .login-page-container {
          min-height: 100vh;
          display: flex;
          align-items: center;
          justify-content: center;
          background: linear-gradient(135deg, #0a192f 0%, #0f2744 50%, #1e3a8a 100%);
          padding: 1.5rem;
          font-family: var(--font-sans, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif);
        }

        .login-card {
          width: 100%;
          max-width: 480px;
          background: #ffffff;
          border-radius: 14px;
          box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.25), 0 10px 10px -5px rgba(0, 0, 0, 0.1);
          overflow: hidden;
          border: 1px solid rgba(255, 255, 255, 0.12);
        }

        .login-brand-section {
          padding: 2.25rem 2rem 1.5rem 2rem;
          text-align: center;
          background: #ffffff;
        }

        .login-logo-badge {
          width: 64px;
          height: 64px;
          margin: 0 auto 1.25rem auto;
          background: linear-gradient(135deg, #1e3a8a 0%, #0f2744 100%);
          border-radius: 14px;
          display: flex;
          align-items: center;
          justify-content: center;
          box-shadow: 0 4px 12px rgba(15, 39, 68, 0.25);
        }

        .login-brand-title {
          font-size: 1.75rem;
          font-weight: 700;
          color: #0f172a;
          letter-spacing: -0.025em;
          margin-bottom: 0.25rem;
        }

        .login-app-subtitle {
          font-size: 1rem;
          font-weight: 600;
          color: #1e3a8a;
          margin-bottom: 0.5rem;
        }

        .login-description {
          font-size: 0.8125rem;
          color: #64748b;
          line-height: 1.4;
        }

        .login-divider {
          height: 1px;
          background: #e2e8f0;
          margin: 0 2rem;
        }

        .portal-selection-section {
          padding: 1.75rem 2rem;
        }

        .portal-selection-intro {
          font-size: 0.875rem;
          font-weight: 600;
          color: #334155;
          text-align: center;
          margin-bottom: 1.25rem;
        }

        .portal-cards-grid {
          display: flex;
          flex-direction: column;
          gap: 1rem;
        }

        .portal-choice-card {
          border: 1px solid #e2e8f0;
          border-radius: 10px;
          padding: 1.25rem;
          cursor: pointer;
          transition: all 0.2s ease;
          background: #f8fafc;
          display: flex;
          flex-direction: column;
          gap: 0.875rem;
        }

        .portal-choice-card:hover, .portal-choice-card:focus {
          border-color: #2563eb;
          background: #ffffff;
          box-shadow: 0 4px 12px rgba(37, 99, 235, 0.08);
          transform: translateY(-1px);
        }

        .portal-choice-icon-wrap {
          width: 44px;
          height: 44px;
          border-radius: 10px;
          display: flex;
          align-items: center;
          justify-content: center;
        }

        .customer-icon {
          background: #eff6ff;
        }

        .officer-icon {
          background: #f0fdf4;
        }

        .portal-choice-info {
          display: flex;
          flex-direction: column;
          gap: 0.25rem;
        }

        .portal-choice-title {
          font-size: 1rem;
          font-weight: 700;
          color: #0f172a;
          margin: 0;
        }

        .portal-choice-desc {
          font-size: 0.8125rem;
          color: #64748b;
          line-height: 1.4;
          margin: 0;
        }

        .portal-choice-btn {
          display: flex;
          align-items: center;
          justify-content: center;
          gap: 0.5rem;
          padding: 0.625rem 1rem;
          border-radius: 6px;
          font-size: 0.875rem;
          font-weight: 600;
          cursor: pointer;
          border: none;
          transition: background-color 0.15s ease;
        }

        .btn-customer {
          background: #2563eb;
          color: #ffffff;
        }

        .btn-customer:hover {
          background: #1d4ed8;
        }

        .btn-officer {
          background: #0f766e;
          color: #ffffff;
        }

        .btn-officer:hover {
          background: #115e59;
        }

        .login-action-section {
          padding: 1.75rem 2rem;
          display: flex;
          flex-direction: column;
          align-items: center;
        }

        .back-portal-link {
          align-self: flex-start;
          display: flex;
          align-items: center;
          gap: 0.375rem;
          background: none;
          border: none;
          color: #64748b;
          font-size: 0.8125rem;
          font-weight: 600;
          cursor: pointer;
          margin-bottom: 1rem;
          padding: 0;
        }

        .back-portal-link:hover {
          color: #1e3a8a;
        }

        .active-portal-badge {
          display: flex;
          align-items: center;
          gap: 0.5rem;
          background: #f1f5f9;
          padding: 0.375rem 0.875rem;
          border-radius: 20px;
          font-size: 0.8125rem;
          font-weight: 600;
          color: #1e293b;
          margin-bottom: 1rem;
        }

        .login-instruction {
          font-size: 0.875rem;
          color: #475569;
          text-align: center;
          line-height: 1.5;
          margin-bottom: 1.5rem;
        }

        .login-error-banner {
          width: 100%;
          display: flex;
          align-items: center;
          gap: 0.625rem;
          padding: 0.75rem 1rem;
          background-color: #fef2f2;
          border: 1px solid #fecaca;
          border-radius: 8px;
          color: #991b1b;
          font-size: 0.8125rem;
          margin-bottom: 1.25rem;
          line-height: 1.4;
        }

        .login-error-icon {
          flex-shrink: 0;
        }

        .login-button-wrapper {
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          min-height: 48px;
          margin-bottom: 0.5rem;
          width: 100%;
        }

        .google-btn-slot {
          display: flex;
          justify-content: center;
          width: 100%;
        }

        .login-loading-state {
          display: flex;
          align-items: center;
          gap: 0.75rem;
          padding: 0.75rem 1.25rem;
          background: #f1f5f9;
          border-radius: 8px;
          color: #1e3a8a;
          font-size: 0.875rem;
          font-weight: 500;
        }

        .login-spinner-icon {
          animation: spin 1s linear infinite;
        }

        @keyframes spin {
          0% { transform: rotate(0deg); }
          100% { transform: rotate(360deg); }
        }

        .login-footer {
          padding: 1rem 2rem 1.5rem 2rem;
          background: #f8fafc;
          border-top: 1px solid #e2e8f0;
          text-align: center;
        }

        .login-security-notice {
          font-size: 0.75rem;
          color: #94a3b8;
          font-weight: 500;
        }
      `}</style>
    </div>
  );
}

export default LoginPage;
