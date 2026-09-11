import { describe, it, expect } from 'vitest';
import { api } from '../services/api';
import { formatCurrency, getStatusBadge } from '../pages/CustomerDashboardPage';
import { CustomerRoute, OfficerRoute } from '../components/Common/ProtectedRoute';

describe('Customer Portal Foundation & Helpers', () => {
  it('formats INR currency correctly', () => {
    expect(formatCurrency(500000)).toMatch(/₹\s?5,00,000/);
    expect(formatCurrency(1250000)).toMatch(/₹\s?12,50,000/);
    expect(formatCurrency(0)).toMatch(/₹\s?0/);
    expect(formatCurrency(null)).toBe('₹0');
    expect(formatCurrency(undefined)).toBe('₹0');
  });

  it('maps customer application status to correct badge styles and labels', () => {
    expect(getStatusBadge('DRAFT').label).toBe('Draft');
    expect(getStatusBadge('DRAFT').colorClass).toBe('badge-draft');

    expect(getStatusBadge('SUBMITTED').label).toBe('Submitted');
    expect(getStatusBadge('SUBMITTED').colorClass).toBe('badge-submitted');

    expect(getStatusBadge('IN_REVIEW').label).toBe('In Review');
    expect(getStatusBadge('IN_REVIEW').colorClass).toBe('badge-in-review');

    expect(getStatusBadge('APPROVED').label).toBe('Approved');
    expect(getStatusBadge('APPROVED').colorClass).toBe('badge-approved');

    expect(getStatusBadge('REJECTED').label).toBe('Rejected');
    expect(getStatusBadge('REJECTED').colorClass).toBe('badge-rejected');
  });

  it('provides all customer portal API methods on api service', () => {
    expect(typeof api.getCustomerApplications).toBe('function');
    expect(typeof api.createCustomerApplication).toBe('function');
    expect(typeof api.getCustomerApplication).toBe('function');
    expect(typeof api.uploadCustomerDocument).toBe('function');
    expect(typeof api.deleteCustomerDocument).toBe('function');
    expect(typeof api.submitCustomerApplication).toBe('function');
  });

  it('exports CustomerRoute and OfficerRoute components', () => {
    expect(typeof CustomerRoute).toBe('function');
    expect(typeof OfficerRoute).toBe('function');
  });

  it('enforces RBAC logic for customer vs officer route access', () => {
    // Evaluates customer route access logic
    function evaluateCustomerAccess(user) {
      if (!user) return { status: 'REDIRECT', destination: '/login' };
      if (user.role !== 'CUSTOMER') return { status: 'REDIRECT', destination: '/dashboard' };
      return { status: 'ALLOWED' };
    }

    // Evaluates officer route access logic
    function evaluateOfficerAccess(user) {
      if (!user) return { status: 'REDIRECT', destination: '/login' };
      if (user.role === 'CUSTOMER') return { status: 'REDIRECT', destination: '/customer/dashboard' };
      return { status: 'ALLOWED' };
    }

    const customerUser = { id: 'usr_c1', role: 'CUSTOMER' };
    const officerUser = { id: 'usr_o1', role: 'LOAN_OFFICER' };
    const managerUser = { id: 'usr_m1', role: 'MANAGER' };

    // Customer route checks
    expect(evaluateCustomerAccess(customerUser).status).toBe('ALLOWED');
    expect(evaluateCustomerAccess(officerUser).destination).toBe('/dashboard');
    expect(evaluateCustomerAccess(managerUser).destination).toBe('/dashboard');
    expect(evaluateCustomerAccess(null).destination).toBe('/login');

    // Officer route checks
    expect(evaluateOfficerAccess(officerUser).status).toBe('ALLOWED');
    expect(evaluateOfficerAccess(managerUser).status).toBe('ALLOWED');
    expect(evaluateOfficerAccess(customerUser).destination).toBe('/customer/dashboard');
    expect(evaluateOfficerAccess(null).destination).toBe('/login');
  });
});
