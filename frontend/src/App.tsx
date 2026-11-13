import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';
import { ProtectedRoute } from './components/ProtectedRoute';
import { Layout } from './components/Layout';
import { Login } from './pages/Login';
import { ReceptionPanel } from './pages/ReceptionPanel';
import { AdminPanel } from './pages/AdminPanel';
import { OwnerDashboard } from './pages/OwnerDashboard';
import { TrainerPanel } from './pages/TrainerPanel';

const RoleBasedHome: React.FC = () => {
  const { roles, activeRole } = useAuth();
  const currentRole = activeRole || roles[0];

  if (currentRole === 'owner') return <Navigate to="/owner" replace />;
  if (currentRole === 'admin') return <Navigate to="/admin" replace />;
  if (currentRole === 'reception') return <Navigate to="/reception" replace />;
  if (currentRole === 'trainer') return <Navigate to="/trainer" replace />;
  return <Navigate to="/login" replace />;
};

export const App: React.FC = () => {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          {/* Public login route */}
          <Route path="/login" element={<Login />} />

          {/* Protected routes within Staff Shell Layout */}
          <Route element={<ProtectedRoute />}>
            <Route element={<Layout />}>
              <Route path="/" element={<RoleBasedHome />} />

              {/* Owner Dashboard: Owner only */}
              <Route element={<ProtectedRoute allowedRoles={['owner']} />}>
                <Route path="/owner" element={<OwnerDashboard />} />
              </Route>

              {/* Admin Panel: Owner, Admin */}
              <Route element={<ProtectedRoute allowedRoles={['owner', 'admin']} />}>
                <Route path="/admin" element={<AdminPanel />} />
              </Route>

              {/* Reception Desk: Owner, Admin, Reception */}
              <Route element={<ProtectedRoute allowedRoles={['owner', 'admin', 'reception']} />}>
                <Route path="/reception" element={<ReceptionPanel />} />
              </Route>

              {/* Trainer Hub: Owner, Admin, Trainer */}
              <Route element={<ProtectedRoute allowedRoles={['owner', 'admin', 'trainer']} />}>
                <Route path="/trainer" element={<TrainerPanel />} />
              </Route>
            </Route>
          </Route>

          {/* Catch-all redirect */}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  );
};

