import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';
import {
  ProtectedRoute,
  PublicOnlyRoute,
  CustomerRoute,
  OfficerRoute,
} from './components/Common/ProtectedRoute';
import { LoginPage } from './pages/LoginPage';
import { AppLayout } from './components/Layout/AppLayout';
import { DashboardPage } from './pages/DashboardPage';
import { ApplicationsPage } from './pages/ApplicationsPage';
import { ApplicationDetailPage } from './pages/ApplicationDetailPage';
import { PoliciesPage } from './pages/PoliciesPage';

// Customer Portal Components
import { CustomerLayout } from './components/Customer/CustomerLayout';
import { CustomerDashboardPage } from './pages/CustomerDashboardPage';
import { CreateApplicationPage } from './pages/CreateApplicationPage';
import { CustomerApplicationDetailPage } from './pages/CustomerApplicationDetailPage';

// Explicit root route redirector based on authenticated role
function RootRedirector() {
  const { user, loading } = useAuth();
  console.log('[AUTH DEBUG] RootRedirector evaluated:', { loading, userRole: user?.role, userId: user?.id });

  if (loading) {
    return null;
  }

  if (!user) {
    console.log('[AUTH DEBUG] RootRedirector -> /login (unauthenticated)');
    return <Navigate to="/login" replace />;
  }

  if (user.role === 'CUSTOMER') {
    console.log('[AUTH DEBUG] RootRedirector -> /customer/dashboard (CUSTOMER)');
    return <Navigate to="/customer/dashboard" replace />;
  }

  console.log('[AUTH DEBUG] RootRedirector -> /dashboard (LOAN_OFFICER/MANAGER)');
  return <Navigate to="/dashboard" replace />;
}

export function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          {/* Public Portal Selection & Authentication */}
          <Route
            path="/login"
            element={
              <PublicOnlyRoute>
                <LoginPage />
              </PublicOnlyRoute>
            }
          />

          {/* Root Redirector based on role / auth */}
          <Route path="/" element={<RootRedirector />} />

          {/* Customer / Applicant Portal Routes */}
          <Route
            path="/customer"
            element={
              <CustomerRoute>
                <CustomerLayout />
              </CustomerRoute>
            }
          >
            <Route index element={<Navigate to="/customer/dashboard" replace />} />
            <Route path="dashboard" element={<CustomerDashboardPage />} />
            <Route path="applications/new" element={<CreateApplicationPage />} />
            <Route path="applications/:applicationId" element={<CustomerApplicationDetailPage />} />
            <Route path="*" element={<Navigate to="/customer/dashboard" replace />} />
          </Route>

          {/* Loan Officer & Manager Underwriting Portal Routes */}
          <Route
            element={
              <OfficerRoute>
                <AppLayout />
              </OfficerRoute>
            }
          >
            <Route path="/dashboard" element={<DashboardPage />} />
            <Route path="/applications" element={<ApplicationsPage />} />
            <Route path="/applications/:applicationId" element={<ApplicationDetailPage />} />
            <Route path="/policies" element={<PoliciesPage />} />
          </Route>

          {/* Fallback */}
          <Route path="*" element={<Navigate to="/login" replace />} />
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  );
}

export default App;
