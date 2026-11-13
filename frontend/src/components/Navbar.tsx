import React from 'react';
import { useAuth } from '../context/AuthContext';
import { LogOut, Dumbbell, ShieldCheck } from 'lucide-react';

export const Navbar: React.FC = () => {
  const { user, roles, activeRole, switchRole, logout } = useAuth();

  return (
    <header className="bg-slate-900 border-b border-slate-800 text-white sticky top-0 z-30">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        {/* Left: Branding */}
        <div className="flex items-center space-x-3">
          <div className="w-10 h-10 rounded-lg bg-emerald-500/20 border border-emerald-500/40 flex items-center justify-center text-emerald-400">
            <Dumbbell className="w-6 h-6" />
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <span className="font-bold text-lg tracking-tight">GymOS</span>
              <span className="bg-emerald-500/10 text-emerald-400 text-xs px-2 py-0.5 rounded border border-emerald-500/20">
                Staff Ops
              </span>
            </div>
            <p className="text-xs text-slate-400">
              Gym #{user?.gym_id ?? 1} • {user?.branch_id ? `Branch #${user.branch_id}` : 'Main Branch'}
            </p>
          </div>
        </div>

        {/* Right: User profile, Role selector & Logout */}
        <div className="flex items-center space-x-4">
          {/* Multi-role switcher if user has more than 1 role */}
          {roles.length > 1 ? (
            <div className="flex items-center space-x-1 bg-slate-800 p-1 rounded-lg border border-slate-700 text-xs">
              <ShieldCheck className="w-4 h-4 text-emerald-400 ml-1" />
              {roles.map((r) => (
                <button
                  key={r}
                  onClick={() => switchRole(r)}
                  className={`px-2 py-1 rounded capitalize font-medium transition ${
                    activeRole === r
                      ? 'bg-emerald-600 text-white shadow-sm'
                      : 'text-slate-400 hover:text-white'
                  }`}
                >
                  {r}
                </button>
              ))}
            </div>
          ) : (
            <div className="flex items-center space-x-1.5 px-2.5 py-1 rounded bg-slate-800 border border-slate-700 text-xs">
              <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
              <span className="capitalize text-slate-200 font-medium">
                {activeRole || roles[0] || 'Staff'}
              </span>
            </div>
          )}

          <div className="text-right hidden sm:block">
            <div className="text-xs font-medium text-slate-200">
              {user?.full_name || user?.email || 'Logged In'}
            </div>
            <div className="text-[10px] text-slate-400">{user?.email}</div>
          </div>

          <button
            onClick={logout}
            className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg text-xs font-medium bg-rose-500/10 text-rose-300 hover:bg-rose-500/20 border border-rose-500/20 transition"
            title="Sign out"
          >
            <LogOut className="w-3.5 h-3.5" />
            <span className="hidden sm:inline">Logout</span>
          </button>
        </div>
      </div>
    </header>
  );
};

