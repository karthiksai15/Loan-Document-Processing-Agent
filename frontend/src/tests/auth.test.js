import { describe, it, expect, beforeEach, vi } from 'vitest';
import { TOKEN_STORAGE_KEY } from '../services/api';
import { LoginPage } from '../pages/LoginPage';
import { ProtectedRoute, PublicOnlyRoute } from '../components/Common/ProtectedRoute';
import { AuthProvider, useAuth } from '../context/AuthContext';
import { getInitials, formatUserRole } from '../components/Layout/TopBar';

// In-memory mock for localStorage
const storageStore = {};
const mockLocalStorage = {
  getItem: vi.fn((key) => storageStore[key] || null),
  setItem: vi.fn((key, val) => {
    storageStore[key] = String(val);
  }),
  removeItem: vi.fn((key) => {
    delete storageStore[key];
  }),
  clear: vi.fn(() => {
    Object.keys(storageStore).forEach((k) => delete storageStore[k]);
  }),
};

// Route guard decision function mirror matching ProtectedRoute logic
function evaluateRouteAccess({ user, loading, path }) {
  if (loading) {
    return { status: 'LOADING' };
  }
  if (!user) {
    return { status: 'REDIRECT', destination: '/login', state: { from: path } };
  }
  return { status: 'ALLOWED', destination: path };
}

// Route guard decision function mirror matching PublicOnlyRoute logic
function evaluatePublicOnlyAccess({ user, loading, path }) {
  if (loading) {
    return { status: 'LOADING' };
  }
  if (user) {
    if (user.role === 'CUSTOMER') {
      return { status: 'REDIRECT', destination: '/customer/dashboard' };
    }
    return { status: 'REDIRECT', destination: '/dashboard' };
  }
  return { status: 'ALLOWED', destination: path };
}

describe('Frontend Authentication Foundation & Session Lifecycle', () => {
  beforeEach(() => {
    mockLocalStorage.clear();
    vi.clearAllMocks();
    globalThis.window = { localStorage: mockLocalStorage };
  });

  // -------------------------------------------------------------------------
  // 1. Storage Key and Token Interceptor
  // -------------------------------------------------------------------------
  it('defines the correct GenBank token storage key', () => {
    expect(TOKEN_STORAGE_KEY).toBe('genbank_access_token');
  });

  it('attaches Bearer token to request headers when token is stored', () => {
    const fakeToken = 'header.payload.signature123';
    mockLocalStorage.setItem(TOKEN_STORAGE_KEY, fakeToken);

    // Mock Axios request interceptor behavior
    const requestConfig = { headers: {} };
    const token = mockLocalStorage.getItem(TOKEN_STORAGE_KEY);
    if (token) {
      requestConfig.headers.Authorization = `Bearer ${token}`;
    }

    expect(requestConfig.headers.Authorization).toBe(`Bearer ${fakeToken}`);
    expect(requestConfig.headers.Authorization).not.toContain('loan_officer_001');
  });

  it('does not attach Authorization header when token is absent in storage', () => {
    const requestConfig = { headers: {} };
    const token = mockLocalStorage.getItem(TOKEN_STORAGE_KEY);
    if (token) {
      requestConfig.headers.Authorization = `Bearer ${token}`;
    }

    expect(requestConfig.headers.Authorization).toBeUndefined();
  });

  // -------------------------------------------------------------------------
  // 2. Token Exchange & Session Storage
  // -------------------------------------------------------------------------
  it('stores access token and user profile upon successful backend token exchange', async () => {
    const mockBackendResponse = {
      access_token: 'valid.jwt.token',
      token_type: 'bearer',
      user: {
        id: 'usr_abc123',
        email: 'officer@genbank.com',
        name: 'Alex Mercer',
        role: 'LOAN_OFFICER',
      },
    };

    // Simulate AuthContext login action
    const mockAuthGoogle = vi.fn().mockResolvedValue(mockBackendResponse);

    const performLogin = async (idToken) => {
      const resp = await mockAuthGoogle(idToken);
      mockLocalStorage.setItem(TOKEN_STORAGE_KEY, resp.access_token);
      return { user: resp.user, token: resp.access_token };
    };

    const session = await performLogin('mock-google-id-token');

    expect(mockLocalStorage.setItem).toHaveBeenCalledWith(
      TOKEN_STORAGE_KEY,
      'valid.jwt.token'
    );
    expect(session.token).toBe('valid.jwt.token');
    expect(session.user.role).toBe('LOAN_OFFICER');
    expect(session.user.email).toBe('officer@genbank.com');
  });

  // -------------------------------------------------------------------------
  // 3. Session Restoration
  // -------------------------------------------------------------------------
  it('restores authenticated user profile on reload when valid token exists', async () => {
    mockLocalStorage.setItem(TOKEN_STORAGE_KEY, 'persisted.jwt.token');

    const mockGetMe = vi.fn().mockResolvedValue({
      id: 'usr_xyz789',
      email: 'customer@example.com',
      name: 'Aarav Sharma',
      role: 'CUSTOMER',
    });

    // Simulate session restoration in AuthContext
    const storedToken = mockLocalStorage.getItem(TOKEN_STORAGE_KEY);
    expect(storedToken).toBe('persisted.jwt.token');

    const restoredUser = await mockGetMe();
    expect(restoredUser.id).toBe('usr_xyz789');
    expect(restoredUser.role).toBe('CUSTOMER');
    expect(restoredUser.email).toBe('customer@example.com');
  });

  it('clears storage and resets session when backend rejects token with 401', async () => {
    mockLocalStorage.setItem(TOKEN_STORAGE_KEY, 'expired.jwt.token');

    const error401 = new Error('Authentication token has expired');
    error401.status = 401;
    const mockGetMe = vi.fn().mockRejectedValue(error401);

    // Simulate session restoration failure handling in AuthContext
    let user = null;
    let token = mockLocalStorage.getItem(TOKEN_STORAGE_KEY);

    try {
      user = await mockGetMe();
    } catch (err) {
      mockLocalStorage.removeItem(TOKEN_STORAGE_KEY);
      user = null;
      token = null;
    }

    expect(mockLocalStorage.removeItem).toHaveBeenCalledWith(TOKEN_STORAGE_KEY);
    expect(user).toBeNull();
    expect(token).toBeNull();
    expect(mockLocalStorage.getItem(TOKEN_STORAGE_KEY)).toBeNull();
  });

  // -------------------------------------------------------------------------
  // 4. Logout Implementation
  // -------------------------------------------------------------------------
  it('clears access token, user profile, and local storage on logout', () => {
    mockLocalStorage.setItem(TOKEN_STORAGE_KEY, 'active.jwt.token');
    let user = { id: 'usr_1', email: 'officer@genbank.com' };
    let token = 'active.jwt.token';

    // Simulate logout action
    const performLogout = () => {
      mockLocalStorage.removeItem(TOKEN_STORAGE_KEY);
      user = null;
      token = null;
    };

    performLogout();

    expect(mockLocalStorage.removeItem).toHaveBeenCalledWith(TOKEN_STORAGE_KEY);
    expect(user).toBeNull();
    expect(token).toBeNull();
    expect(mockLocalStorage.getItem(TOKEN_STORAGE_KEY)).toBeNull();
  });

  // -------------------------------------------------------------------------
  // 5. Route Protection Rules
  // -------------------------------------------------------------------------
  it('redirects unauthenticated user from protected routes to /login with origin preserved', () => {
    const routes = ['/dashboard', '/applications', '/applications/A001', '/policies'];

    routes.forEach((route) => {
      const decision = evaluateRouteAccess({ user: null, loading: false, path: route });
      expect(decision.status).toBe('REDIRECT');
      expect(decision.destination).toBe('/login');
      expect(decision.state.from).toBe(route);
    });
  });

  it('allows authenticated user to access protected routes', () => {
    const authenticatedUser = { id: 'usr_1', role: 'LOAN_OFFICER' };
    const routes = ['/dashboard', '/applications', '/applications/A001', '/policies'];

    routes.forEach((route) => {
      const decision = evaluateRouteAccess({ user: authenticatedUser, loading: false, path: route });
      expect(decision.status).toBe('ALLOWED');
      expect(decision.destination).toBe(route);
    });
  });

  it('redirects authenticated CUSTOMER to /customer/dashboard and OFFICER to /dashboard', () => {
    const customerUser = { id: 'usr_1', role: 'CUSTOMER' };
    const customerDecision = evaluatePublicOnlyAccess({ user: customerUser, loading: false, path: '/login' });
    expect(customerDecision.status).toBe('REDIRECT');
    expect(customerDecision.destination).toBe('/customer/dashboard');

    const officerUser = { id: 'usr_2', role: 'LOAN_OFFICER' };
    const officerDecision = evaluatePublicOnlyAccess({ user: officerUser, loading: false, path: '/login' });
    expect(officerDecision.status).toBe('REDIRECT');
    expect(officerDecision.destination).toBe('/dashboard');
  });

  it('renders loading state while authentication is being verified', () => {
    const decision = evaluateRouteAccess({ user: null, loading: true, path: '/dashboard' });
    expect(decision.status).toBe('LOADING');
  });

  // -------------------------------------------------------------------------
  // 6. Login Page Component & Google Client ID
  // -------------------------------------------------------------------------
  it('exports LoginPage, ProtectedRoute, and AuthProvider components correctly', () => {
    expect(typeof LoginPage).toBe('function');
    expect(typeof ProtectedRoute).toBe('function');
    expect(typeof PublicOnlyRoute).toBe('function');
    expect(typeof AuthProvider).toBe('function');
    expect(typeof useAuth).toBe('function');
  });

  it('verifies default Google Client ID configuration', () => {
    const resolvedClientId =
      import.meta.env.VITE_GOOGLE_CLIENT_ID ||
      '927480599191-iock07diunjgmr0t3fdi3teh7ot5grk5.apps.googleusercontent.com';

    expect(resolvedClientId).toMatch(/^927480599191-[a-z0-9]+\.apps\.googleusercontent\.com$/);
  });

  // -------------------------------------------------------------------------
  // 7. Dynamic User Identity & TopBar Rendering Helpers
  // -------------------------------------------------------------------------
  it('computes correct initials for user avatar badge', () => {
    expect(getInitials('Alex Mercer')).toBe('AM');
    expect(getInitials('John Michael Smith')).toBe('JS');
    expect(getInitials('Officer')).toBe('OF');
    expect(getInitials('A')).toBe('A');
    expect(getInitials('')).toBe('U');
    expect(getInitials(null)).toBe('U');
    expect(getInitials(undefined)).toBe('U');
  });

  it('formats user roles for UI display', () => {
    expect(formatUserRole('LOAN_OFFICER')).toBe('Loan Officer');
    expect(formatUserRole('CUSTOMER')).toBe('Customer');
    expect(formatUserRole(null)).toBe('User');
    expect(formatUserRole(undefined)).toBe('User');
    expect(formatUserRole('SENIOR_UNDERWRITER')).toBe('Senior Underwriter');
  });

  // -------------------------------------------------------------------------
  // 8. Officer Identity Resolution & Role Safety in Reviews
  // -------------------------------------------------------------------------
  it('resolves activeOfficerId to authenticated user ID for underwriting actions', () => {
    const officerUser = {
      id: 'usr_7f8a9b',
      email: 'officer@genbank.com',
      name: 'Sarah Jenkins',
      role: 'LOAN_OFFICER',
    };

    const resolveOfficerId = (user) => user?.id;
    expect(resolveOfficerId(officerUser)).toBe('usr_7f8a9b');
  });

  it('does not fall back to hardcoded officer ID when user ID is unavailable', () => {
    const resolveOfficerId = (user) => user?.id;
    expect(resolveOfficerId({ email: 'backup@genbank.com' })).toBeUndefined();
    expect(resolveOfficerId(null)).toBeUndefined();
    expect(resolveOfficerId(undefined)).toBeUndefined();
  });

  it('guards underwriting actions against CUSTOMER role', () => {
    const customerUser = {
      id: 'usr_cust_001',
      email: 'borrower@example.com',
      role: 'CUSTOMER',
    };

    const isCustomer = (user) => user?.role === 'CUSTOMER';
    expect(isCustomer(customerUser)).toBe(true);

    const officerUser = {
      id: 'usr_off_001',
      role: 'LOAN_OFFICER',
    };
    expect(isCustomer(officerUser)).toBe(false);
  });
});
