import React from 'react';
import { Navigate, Outlet } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { UserRole } from '../types/auth';

interface ProtectedRouteProps {
  allowedRoles?: UserRole[];
}

export const ProtectedRoute: React.FC<ProtectedRouteProps> = ({ allowedRoles }) => {
  const { isAuthenticated, isLoading, roles } = useAuth();

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-slate-100">
        <div className="text-center">
          <div className="w-12 h-12 border-4 border-emerald-600 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
          <p className="text-slate-600 font-medium">Loading GymOS...</p>
        </div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  if (allowedRoles && !allowedRoles.some((r) => roles.includes(r))) {
    // If not authorized for this specific route, redirect to the primary role's default view
    if (roles.includes('owner')) return <Navigate to="/owner" replace />;
    if (roles.includes('admin')) return <Navigate to="/admin" replace />;
    if (roles.includes('reception')) return <Navigate to="/reception" replace />;
    if (roles.includes('trainer')) return <Navigate to="/trainer" replace />;
    return <Navigate to="/unauthorized" replace />;
  }

  return <Outlet />;
};

