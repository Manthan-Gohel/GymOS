import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { Dumbbell, LogIn, AlertCircle } from 'lucide-react';

export const Login: React.FC = () => {
  const [gymId, setGymId] = useState<number>(1);
  const [email, setEmail] = useState<string>('reception@example.com');
  const [password, setPassword] = useState<string>('secret123');
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);

  const { login } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setIsSubmitting(true);
    try {
      await login({
        gym_id: Number(gymId),
        email,
        password,
      });
      navigate('/');
    } catch (err: any) {
      setError(err.message || 'Login failed. Please check credentials.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const setPreset = (roleEmail: string) => {
    setEmail(roleEmail);
    setPassword('secret123');
    setGymId(1);
  };

  return (
    <div className="min-h-screen bg-slate-900 flex flex-col justify-center py-12 sm:px-6 lg:px-8">
      <div className="sm:mx-auto sm:w-full sm:max-w-md">
        <div className="flex justify-center">
          <div className="w-14 h-14 rounded-2xl bg-emerald-500/20 border border-emerald-500/40 flex items-center justify-center text-emerald-400 shadow-xl">
            <Dumbbell className="w-8 h-8" />
          </div>
        </div>
        <h2 className="mt-4 text-center text-3xl font-extrabold text-white tracking-tight">
          GymOS Staff Portal
        </h2>
        <p className="mt-2 text-center text-sm text-slate-400">
          Owner, Admin, Reception & Trainer operations
        </p>
      </div>

      <div className="mt-8 sm:mx-auto sm:w-full sm:max-w-md">
        <div className="bg-slate-800 py-8 px-4 shadow-2xl border border-slate-700 sm:rounded-2xl sm:px-10">
          {error && (
            <div className="mb-6 p-4 rounded-lg bg-rose-500/10 border border-rose-500/20 flex items-start space-x-3 text-rose-300 text-sm">
              <AlertCircle className="w-5 h-5 flex-shrink-0 mt-0.5 text-rose-400" />
              <span>{error}</span>
            </div>
          )}

          <form className="space-y-5" onSubmit={handleSubmit}>
            <div>
              <label htmlFor="gymId" className="block text-xs font-semibold text-slate-300 uppercase">
                Gym ID
              </label>
              <input
                id="gymId"
                type="number"
                required
                value={gymId}
                onChange={(e) => setGymId(Number(e.target.value))}
                className="mt-1 block w-full px-3.5 py-2.5 bg-slate-900/80 border border-slate-700 rounded-lg text-white text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-transparent transition"
              />
            </div>

            <div>
              <label htmlFor="email" className="block text-xs font-semibold text-slate-300 uppercase">
                Staff Email
              </label>
              <input
                id="email"
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="mt-1 block w-full px-3.5 py-2.5 bg-slate-900/80 border border-slate-700 rounded-lg text-white text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-transparent transition"
                placeholder="staff@gym.com"
              />
            </div>

            <div>
              <label htmlFor="password" className="block text-xs font-semibold text-slate-300 uppercase">
                Password
              </label>
              <input
                id="password"
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="mt-1 block w-full px-3.5 py-2.5 bg-slate-900/80 border border-slate-700 rounded-lg text-white text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-transparent transition"
              />
            </div>

            <button
              type="submit"
              disabled={isSubmitting}
              className="w-full mt-2 flex justify-center items-center space-x-2 py-3 px-4 border border-transparent rounded-lg text-sm font-semibold text-white bg-emerald-600 hover:bg-emerald-500 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-emerald-500 disabled:opacity-50 transition shadow-lg shadow-emerald-900/20"
            >
              <LogIn className="w-4 h-4" />
              <span>{isSubmitting ? 'Signing in...' : 'Sign in to Staff Panel'}</span>
            </button>
          </form>

          {/* Preset Buttons for Quick Demo Testing */}
          <div className="mt-6 pt-6 border-t border-slate-700">
            <p className="text-xs font-semibold text-slate-400 mb-2 uppercase">Quick Demo Credentials:</p>
            <div className="grid grid-cols-2 gap-2 text-xs">
              <button
                type="button"
                onClick={() => setPreset('owner@example.com')}
                className="px-2.5 py-1.5 rounded bg-slate-700/60 hover:bg-slate-700 text-slate-300 border border-slate-600 text-left"
              >
                Owner
              </button>
              <button
                type="button"
                onClick={() => setPreset('admin@example.com')}
                className="px-2.5 py-1.5 rounded bg-slate-700/60 hover:bg-slate-700 text-slate-300 border border-slate-600 text-left"
              >
                Admin
              </button>
              <button
                type="button"
                onClick={() => setPreset('reception@example.com')}
                className="px-2.5 py-1.5 rounded bg-slate-700/60 hover:bg-slate-700 text-slate-300 border border-slate-600 text-left"
              >
                Reception
              </button>
              <button
                type="button"
                onClick={() => setPreset('trainer@example.com')}
                className="px-2.5 py-1.5 rounded bg-slate-700/60 hover:bg-slate-700 text-slate-300 border border-slate-600 text-left"
              >
                Trainer
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
