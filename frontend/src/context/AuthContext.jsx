import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { api, TOKEN_STORAGE_KEY } from '../services/api';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(() => {
    if (typeof window !== 'undefined' && window.localStorage) {
      return window.localStorage.getItem(TOKEN_STORAGE_KEY);
    }
    return null;
  });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Restore authenticated session on initial mount
  useEffect(() => {
    let isMounted = true;

    async function restoreSession() {
      const storedToken = typeof window !== 'undefined' && window.localStorage
        ? window.localStorage.getItem(TOKEN_STORAGE_KEY)
        : null;

      if (!storedToken) {
        if (isMounted) {
          setLoading(false);
        }
        return;
      }

      try {
        // Validate token with backend GET /api/v1/auth/me
        const userData = await api.getMe();
        if (isMounted) {
          console.log('[AUTH DEBUG] AuthContext.restoreSession succeeded. Restored user:', userData);
          setUser(userData);
          setToken(storedToken);
          setLoading(false);
        }
      } catch (err) {
        // If token is expired, invalid, or server rejects it: clear session
        if (isMounted) {
          console.warn('[AUTH DEBUG] AuthContext.restoreSession failed, clearing session:', err.message);
          if (typeof window !== 'undefined' && window.localStorage) {
            window.localStorage.removeItem(TOKEN_STORAGE_KEY);
          }
          setUser(null);
          setToken(null);
          setLoading(false);
        }
      }
    }

    restoreSession();

    return () => {
      isMounted = false;
    };
  }, []);

  // Login handler: exchange Google ID token with backend
  const login = useCallback(async (idToken, rolePreference = null) => {
    setLoading(true);
    setError(null);
    console.log('[AUTH DEBUG] AuthContext.login initiating backend token exchange with rolePreference:', rolePreference);
    try {
      const response = await api.authGoogle(idToken, rolePreference);
      console.log('[AUTH DEBUG] AuthContext.login raw backend response:', response);
      const { access_token, user: userData } = response;

      if (!access_token || !userData) {
        throw new Error('Authentication response did not contain access token or user profile.');
      }

      if (typeof window !== 'undefined' && window.localStorage) {
        window.localStorage.setItem(TOKEN_STORAGE_KEY, access_token);
      }

      console.log('[AUTH DEBUG] AuthContext.login storing token and user profile in state:', userData);
      setToken(access_token);
      setUser(userData);
      setLoading(false);
      return { success: true, user: userData };
    } catch (err) {
      console.error('[AUTH DEBUG] AuthContext.login error:', err);
      const errorMessage =
        err?.message || 'Authentication failed. Please verify your Google credentials.';
      setError(errorMessage);
      setLoading(false);
      throw err;
    }
  }, []);

  // Logout handler: clear token and user state
  const logout = useCallback(() => {
    if (typeof window !== 'undefined' && window.localStorage) {
      window.localStorage.removeItem(TOKEN_STORAGE_KEY);
    }
    setToken(null);
    setUser(null);
    setError(null);
  }, []);

  const value = {
    user,
    token,
    loading,
    error,
    isAuthenticated: Boolean(user && token),
    login,
    logout,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}

export default AuthContext;
