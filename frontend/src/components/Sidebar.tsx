import React from 'react';
import { NavLink } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import {
  LayoutDashboard,
  Shield,
  Users,
  Activity,
} from 'lucide-react';

interface NavItem {
  label: string;
  path: string;
  icon: React.ComponentType<{ className?: string }>;
  roles: string[];
}

export const Sidebar: React.FC = () => {
  const { hasRole } = useAuth();

  const navItems: NavItem[] = [
    {
      label: 'Owner Dashboard',
      path: '/owner',
      icon: LayoutDashboard,
      roles: ['owner'],
    },
    {
      label: 'Admin Panel',
      path: '/admin',
      icon: Shield,
      roles: ['owner', 'admin'],
    },
    {
      label: 'Reception Desk',
      path: '/reception',
      icon: Users,
      roles: ['owner', 'admin', 'reception'],
    },
    {
      label: 'Trainer Hub',
      path: '/trainer',
      icon: Activity,
      roles: ['owner', 'admin', 'trainer'],
    },
  ];

  const visibleItems = navItems.filter((item) =>
    item.roles.some((r) => hasRole(r as any))
  );

  return (
    <aside className="w-64 bg-white border-r border-slate-200 flex flex-col min-h-[calc(100vh-4rem)]">
      <div className="p-4 border-b border-slate-100">
        <h2 className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
          Staff Panels
        </h2>
      </div>
      <nav className="p-3 space-y-1 flex-1">
        {visibleItems.map((item) => {
          const Icon = item.icon;
          return (
            <NavLink
              key={item.path}
              to={item.path}
              className={({ isActive }) =>
                `flex items-center space-x-3 px-3 py-2.5 rounded-lg text-sm font-medium transition ${
                  isActive
                    ? 'bg-emerald-50 text-emerald-700 font-semibold'
                    : 'text-slate-600 hover:bg-slate-50 hover:text-slate-900'
                }`
              }
            >
              <Icon className="w-4 h-4" />
              <span>{item.label}</span>
            </NavLink>
          );
        })}
      </nav>
      <div className="p-4 border-t border-slate-100 bg-slate-50 text-xs text-slate-500">
        <p className="font-semibold text-slate-700">GymOS MVP v0.1</p>
        <p>No member app • Staff tools only</p>
      </div>
    </aside>
  );
};
