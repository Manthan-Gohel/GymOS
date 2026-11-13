import React, { createContext, useContext, useState, useEffect } from 'react';
import { User, UserRole, LoginRequest } from '../types/auth';
import { api } from '../services/api';

interface AuthContextType {
  user: User | null;
  token: string | null;
  roles: UserRole[];
  activeRole: UserRole | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (credentials: LoginRequest) => Promise<void>;
  logout: () => void;
  switchRole: (role: UserRole) => void;
  hasRole: (allowedRoles: UserRole | UserRole[]) => boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  // VULN-008: JWT is never stored in localStorage. Login keeps it in memory; the
  // HttpOnly `gymos_token` cookie restores the session on reload via /auth/me.
  const [token, setToken] = useState<string | null>(null);
  const [user, setUser] = useState<User | null>(null);
  const [activeRole, setActiveRole] = useState<UserRole | null>(() => {
    return (localStorage.getItem('gymos_active_role') as UserRole) || null;
  });
  const [isLoading, setIsLoading] = useState<boolean>(true);

  // Decode JWT payload helper
  const parseTokenRoles = (jwtToken: string): UserRole[] => {
    try {
      const parts = jwtToken.split('.');
      if (parts.length < 2) return [];
      const payload = JSON.parse(atob(parts[1]));
      return payload.roles || [];
    } catch {
      return [];
    }
  };

  useEffect(() => {
    const initAuth = async () => {
      try {
        const profile = await api.getMe();
        setUser(profile);
        const roles = profile.roles || [];
        if (!activeRole || !roles.includes(activeRole)) {
          const defaultRole = roles[0] || null;
          setActiveRole(defaultRole);
          if (defaultRole) localStorage.setItem('gymos_active_role', defaultRole);
        }
      } catch {
        // Not logged in (no valid cookie) — that's a normal cold start, not an error.
        setUser(null);
      }
      setIsLoading(false);
    };

    initAuth();
  }, []);

  const login = async (credentials: LoginRequest) => {
    setIsLoading(true);
    try {
      const response = await api.login(credentials);
      api.setToken(response.access_token);
      setToken(response.access_token);

      // Fetch user profile
      const profile = await api.getMe();
      setUser(profile);
      const roles = profile.roles || parseTokenRoles(response.access_token);
      const initialRole = roles[0] || null;
      setActiveRole(initialRole);
      if (initialRole) {
        localStorage.setItem('gymos_active_role', initialRole);
      }
    } finally {
      setIsLoading(false);
    }
  };

  const logout = () => {
    void api.logout();
    localStorage.removeItem('gymos_active_role');
    setToken(null);
    setUser(null);
    setActiveRole(null);
  };

  const switchRole = (role: UserRole) => {
    const roles = user?.roles || (token ? parseTokenRoles(token) : []);
    if (roles.includes(role)) {
      setActiveRole(role);
      localStorage.setItem('gymos_active_role', role);
    }
  };

  const hasRole = (allowedRoles: UserRole | UserRole[]): boolean => {
    const roles = user?.roles || (token ? parseTokenRoles(token) : []);
    const checkRoles = Array.isArray(allowedRoles) ? allowedRoles : [allowedRoles];
    return checkRoles.some((r) => roles.includes(r));
  };

  const roles = user?.roles || (token ? parseTokenRoles(token) : []);

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        roles,
        activeRole,
        isAuthenticated: !!user,
        isLoading,
        login,
        logout,
        switchRole,
        hasRole,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

