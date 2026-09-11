import React from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { LoadingState } from './LoadingState';

/**
 * Enforces authentication on private routes.
 * While session validation is pending, displays a clean loading state.
 * If unauthenticated, redirects to /login preserving the requested path.
 */
export function ProtectedRoute({ children }) {
  const { user, loading } = useAuth();
  const location = useLocation();

  if (loading) {
    return (
      <div
        style={{
          minHeight: '100vh',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          backgroundColor: 'var(--color-bg-app, #f8fafc)',
        }}
      >
        <LoadingState message="Verifying authentication..." />
      </div>
    );
  }

  if (!user) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  return children;
}

/**
 * Restricts access to public routes (e.g., /login) for already authenticated users.
 * Automatically forwards authenticated users to their respective role-based dashboard.
 */
export function PublicOnlyRoute({ children }) {
  const { user, loading } = useAuth();
  console.log('[AUTH DEBUG] PublicOnlyRoute evaluated:', { loading, userRole: user?.role, userId: user?.id });

  if (loading) {
    return null;
  }

  if (user) {
    if (user.role === 'CUSTOMER') {
      console.log('[AUTH DEBUG] PublicOnlyRoute -> /customer/dashboard (CUSTOMER already authenticated)');
      return <Navigate to="/customer/dashboard" replace />;
    }
    console.log('[AUTH DEBUG] PublicOnlyRoute -> /dashboard (OFFICER/MANAGER already authenticated)');
    return <Navigate to="/dashboard" replace />;
  }

  return children;
}

/**
 * Route protection exclusively for Applicants/Customers.
 * If user is Loan Officer or Manager, redirects them to /dashboard.
 */
export function CustomerRoute({ children }) {
  const { user, loading } = useAuth();
  const location = useLocation();
  console.log('[AUTH DEBUG] CustomerRoute evaluated:', { loading, userRole: user?.role, path: location.pathname });

  if (loading) {
    return (
      <div
        style={{
          minHeight: '100vh',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          backgroundColor: 'var(--color-bg-app, #f8fafc)',
        }}
      >
        <LoadingState message="Verifying authentication..." />
      </div>
    );
  }

  if (!user) {
    console.log('[AUTH DEBUG] CustomerRoute -> /login (unauthenticated access to customer route)');
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  if (user.role !== 'CUSTOMER') {
    console.log('[AUTH DEBUG] CustomerRoute -> /dashboard (non-customer attempted customer route)');
    return <Navigate to="/dashboard" replace />;
  }

  return children;
}

/**
 * Route protection exclusively for Loan Officers & Managers.
 * If user is Customer, redirects them to /customer/dashboard.
 */
export function OfficerRoute({ children }) {
  const { user, loading } = useAuth();
  const location = useLocation();
  console.log('[AUTH DEBUG] OfficerRoute evaluated:', { loading, userRole: user?.role, path: location.pathname });

  if (loading) {
    return (
      <div
        style={{
          minHeight: '100vh',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          backgroundColor: 'var(--color-bg-app, #f8fafc)',
        }}
      >
        <LoadingState message="Verifying authentication..." />
      </div>
    );
  }

  if (!user) {
    console.log('[AUTH DEBUG] OfficerRoute -> /login (unauthenticated access to officer route)');
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  if (user.role === 'CUSTOMER') {
    console.log('[AUTH DEBUG] OfficerRoute -> /customer/dashboard (CUSTOMER attempted officer route)');
    return <Navigate to="/customer/dashboard" replace />;
  }

  return children;
}
