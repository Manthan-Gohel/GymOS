import React, { useState, useEffect } from 'react';
import { api } from '../services/api';
import { MembershipPlan, CreatePlanPayload } from '../types/plan';
import {
  Shield,
  Plus,
  Clock,
  Layers,
  Wrench,
  DollarSign,
  UserCheck,
  Check,
  ToggleLeft,
  ToggleRight,
  RefreshCw,
} from 'lucide-react';

export const AdminPanel: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'plans' | 'staff' | 'expenses' | 'equipment'>('plans');
  const [plans, setPlans] = useState<MembershipPlan[]>([]);
  const [loading, setLoading] = useState(true);
  const [showAddPlan, setShowAddPlan] = useState(false);

  // New Plan form state
  const [newPlan, setNewPlan] = useState<CreatePlanPayload>({
    name: '',
    duration_days: 30,
    price_paise: 150000,
    currency: 'INR',
  });
  const [planPriceRupees, setPlanPriceRupees] = useState<number>(1500);

  // Mock staff & equipment state for MVP
  const [staffMembers] = useState([
    { id: 1, name: 'Sanjay Owner', role: 'owner', email: 'owner@example.com', presentToday: true },
    { id: 2, name: 'Vikram Admin', role: 'admin', email: 'admin@example.com', presentToday: true },
    { id: 3, name: 'Pooja Reception', role: 'reception', email: 'reception@example.com', presentToday: true },
    { id: 4, name: 'Arjun Trainer', role: 'trainer', email: 'trainer@example.com', presentToday: false },
  ]);

  const [expenses, setExpenses] = useState([
    { id: 1, title: 'Electricity Bill', category: 'Utilities', amount: 12500, date: '2026-11-10' },
    { id: 2, title: 'Dumbbell Rack Repair', category: 'Maintenance', amount: 2200, date: '2026-11-12' },
  ]);

  const [equipmentList] = useState([
    { id: 1, name: 'Treadmill Commercial X2', status: 'operational', nextService: '2026-12-01' },
    { id: 2, name: 'Smith Machine Pro', status: 'operational', nextService: '2026-11-20' },
    { id: 3, name: 'Cable Crossover Tower', status: 'needs_service', nextService: '2026-11-15' },
  ]);

  const loadPlans = async () => {
    setLoading(true);
    try {
      const data = await api.getPlans();
      setPlans(data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadPlans();
  }, []);

  const handleCreatePlan = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const payload: CreatePlanPayload = {
        ...newPlan,
        price_paise: Math.round(Number(planPriceRupees) * 100),
      };
      const created = await api.createPlan(payload);
      setPlans([created, ...plans]);
      setShowAddPlan(false);
      setNewPlan({
        name: '',
        duration_days: 30,
        price_paise: 150000,
        currency: 'INR',
      });
      setPlanPriceRupees(1500);
      alert('Membership plan created successfully!');
    } catch (err: any) {
      alert(`Error creating plan: ${err.message}`);
    }
  };

  const handleTogglePlan = async (plan: MembershipPlan) => {
    try {
      const updated = await api.updatePlan(plan.id, { is_active: !plan.is_active });
      setPlans(plans.map((p) => (p.id === plan.id ? updated : p)));
    } catch (err: any) {
      alert(`Error updating plan: ${err.message}`);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight flex items-center space-x-2">
            <Shield className="w-7 h-7 text-indigo-600" />
            <span>Admin Control Panel</span>
          </h1>
          <p className="text-sm text-slate-500">
            Configure gym plans, manage staff records, track expenses and maintenance
          </p>
        </div>

        <div className="flex items-center space-x-3">
          <button
            onClick={loadPlans}
            className="p-2 text-slate-500 hover:text-slate-800 hover:bg-slate-100 rounded-lg transition"
            title="Refresh"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Tabs */}
      <div className="border-b border-slate-200 flex space-x-6">
        <button
          onClick={() => setActiveTab('plans')}
          className={`pb-3 text-sm font-semibold flex items-center space-x-2 border-b-2 transition ${
            activeTab === 'plans'
              ? 'border-indigo-600 text-indigo-600'
              : 'border-transparent text-slate-500 hover:text-slate-800'
          }`}
        >
          <Layers className="w-4 h-4" />
          <span>Membership Plans</span>
        </button>

        <button
          onClick={() => setActiveTab('staff')}
          className={`pb-3 text-sm font-semibold flex items-center space-x-2 border-b-2 transition ${
            activeTab === 'staff'
              ? 'border-indigo-600 text-indigo-600'
              : 'border-transparent text-slate-500 hover:text-slate-800'
          }`}
        >
          <UserCheck className="w-4 h-4" />
          <span>Staff & Attendance</span>
        </button>

        <button
          onClick={() => setActiveTab('expenses')}
          className={`pb-3 text-sm font-semibold flex items-center space-x-2 border-b-2 transition ${
            activeTab === 'expenses'
              ? 'border-indigo-600 text-indigo-600'
              : 'border-transparent text-slate-500 hover:text-slate-800'
          }`}
        >
          <DollarSign className="w-4 h-4" />
          <span>Operational Expenses</span>
        </button>

        <button
          onClick={() => setActiveTab('equipment')}
          className={`pb-3 text-sm font-semibold flex items-center space-x-2 border-b-2 transition ${
            activeTab === 'equipment'
              ? 'border-indigo-600 text-indigo-600'
              : 'border-transparent text-slate-500 hover:text-slate-800'
          }`}
        >
          <Wrench className="w-4 h-4" />
          <span>Equipment & Maintenance</span>
        </button>
      </div>

      {/* TAB 1: MEMBERSHIP PLANS */}
      {activeTab === 'plans' && (
        <div className="space-y-4">
          <div className="flex justify-between items-center">
            <h3 className="font-bold text-slate-800 text-base">Configured Membership Plans</h3>
            <button
              onClick={() => setShowAddPlan(true)}
              className="flex items-center space-x-2 px-3.5 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-xs font-semibold shadow-sm transition"
            >
              <Plus className="w-4 h-4" />
              <span>Create New Plan</span>
            </button>
          </div>

          <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
            <table className="w-full text-left text-sm">
              <thead className="bg-slate-50 text-slate-500 text-xs font-semibold uppercase tracking-wider border-b border-slate-200">
                <tr>
                  <th className="px-5 py-3">Plan Name</th>
                  <th className="px-5 py-3">Duration</th>
                  <th className="px-5 py-3">Price</th>
                  <th className="px-5 py-3">Status</th>
                  <th className="px-5 py-3 text-right">Toggle Active</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {loading ? (
                  <tr>
                    <td colSpan={5} className="p-8 text-center text-slate-400">
                      Loading plans...
                    </td>
                  </tr>
                ) : plans.length === 0 ? (
                  <tr>
                    <td colSpan={5} className="p-8 text-center text-slate-400">
                      No plans configured yet.
                    </td>
                  </tr>
                ) : (
                  plans.map((p) => (
                    <tr key={p.id} className="hover:bg-slate-50 transition">
                      <td className="px-5 py-3 font-semibold text-slate-900">{p.name}</td>
                      <td className="px-5 py-3 text-slate-600 flex items-center space-x-1">
                        <Clock className="w-3.5 h-3.5 text-slate-400" />
                        <span>{p.duration_days} Days</span>
                      </td>
                      <td className="px-5 py-3 font-bold text-slate-900">
                        ₹{(p.price_paise / 100).toFixed(2)}
                      </td>
                      <td className="px-5 py-3 text-xs">
                        {p.is_active ? (
                          <span className="px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-800 font-semibold">
                            Active
                          </span>
                        ) : (
                          <span className="px-2 py-0.5 rounded-full bg-slate-200 text-slate-600 font-semibold">
                            Inactive
                          </span>
                        )}
                      </td>
                      <td className="px-5 py-3 text-right">
                        <button
                          onClick={() => handleTogglePlan(p)}
                          className="text-slate-500 hover:text-slate-800 transition"
                          title="Toggle plan active state"
                        >
                          {p.is_active ? (
                            <ToggleRight className="w-6 h-6 text-emerald-600" />
                          ) : (
                            <ToggleLeft className="w-6 h-6 text-slate-400" />
                          )}
                        </button>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* TAB 2: STAFF & ATTENDANCE */}
      {activeTab === 'staff' && (
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-6 space-y-4">
          <div className="flex justify-between items-center mb-2">
            <div>
              <h3 className="font-bold text-slate-900">Manual Staff Attendance & Roster</h3>
              <p className="text-xs text-slate-500">
                Staff check-in logged manually by gym admin. No biometric or facial hardware needed.
              </p>
            </div>
          </div>
          <div className="divide-y divide-slate-100">
            {staffMembers.map((staff) => (
              <div key={staff.id} className="py-3 flex items-center justify-between">
                <div>
                  <div className="font-semibold text-slate-900 text-sm">{staff.name}</div>
                  <div className="text-xs text-slate-400 flex items-center space-x-2">
                    <span className="uppercase font-bold text-indigo-600 bg-indigo-50 px-1.5 py-0.2 rounded text-[10px]">
                      {staff.role}
                    </span>
                    <span>{staff.email}</span>
                  </div>
                </div>
                <div className="flex items-center space-x-3">
                  <span
                    className={`text-xs px-2.5 py-1 rounded-full font-semibold flex items-center space-x-1 ${
                      staff.presentToday
                        ? 'bg-emerald-100 text-emerald-800'
                        : 'bg-rose-100 text-rose-800'
                    }`}
                  >
                    <Check className="w-3 h-3" />
                    <span>{staff.presentToday ? 'Present Today' : 'Absent'}</span>
                  </span>
                  <button className="text-xs text-indigo-600 font-semibold hover:underline">
                    Edit Roster
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* TAB 3: EXPENSES */}
      {activeTab === 'expenses' && (
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-6 space-y-4">
          <div className="flex justify-between items-center">
            <h3 className="font-bold text-slate-900">Operational Expenses Log</h3>
            <button
              onClick={() => {
                const title = prompt('Expense title (e.g. Water bottles):');
                const amount = prompt('Amount in INR:');
                if (title && amount) {
                  setExpenses([
                    ...expenses,
                    {
                      id: expenses.length + 1,
                      title,
                      category: 'General',
                      amount: Number(amount),
                      date: new Date().toISOString().substring(0, 10),
                    },
                  ]);
                }
              }}
              className="px-3 py-1.5 bg-indigo-600 text-white rounded-lg text-xs font-semibold hover:bg-indigo-500"
            >
              + Record Expense
            </button>
          </div>
          <table className="w-full text-left text-sm">
            <thead className="bg-slate-50 text-slate-500 text-xs font-semibold uppercase border-b border-slate-200">
              <tr>
                <th className="px-4 py-2">Item</th>
                <th className="px-4 py-2">Category</th>
                <th className="px-4 py-2">Date</th>
                <th className="px-4 py-2 text-right">Amount (₹)</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {expenses.map((e) => (
                <tr key={e.id}>
                  <td className="px-4 py-2.5 font-medium text-slate-900">{e.title}</td>
                  <td className="px-4 py-2.5 text-xs text-slate-500">{e.category}</td>
                  <td className="px-4 py-2.5 text-xs text-slate-500">{e.date}</td>
                  <td className="px-4 py-2.5 text-right font-bold text-slate-900">
                    ₹{e.amount.toLocaleString()}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* TAB 4: EQUIPMENT */}
      {activeTab === 'equipment' && (
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-6 space-y-4">
          <h3 className="font-bold text-slate-900">Gym Equipment & Maintenance Reminders</h3>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {equipmentList.map((eq) => (
              <div key={eq.id} className="p-4 rounded-xl border border-slate-200 bg-slate-50/50">
                <div className="font-semibold text-slate-900 text-sm">{eq.name}</div>
                <div className="mt-2 flex justify-between items-center text-xs">
                  <span
                    className={`px-2 py-0.5 rounded font-bold uppercase text-[10px] ${
                      eq.status === 'operational'
                        ? 'bg-emerald-100 text-emerald-800'
                        : 'bg-amber-100 text-amber-800'
                    }`}
                  >
                    {eq.status}
                  </span>
                  <span className="text-slate-500">Next: {eq.nextService}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* MODAL: Create Plan */}
      {showAddPlan && (
        <div className="fixed inset-0 bg-slate-900/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-md w-full p-6 shadow-2xl border border-slate-200">
            <h3 className="text-lg font-bold text-slate-900 mb-4">Create Membership Plan</h3>
            <form onSubmit={handleCreatePlan} className="space-y-4 text-sm">
              <div>
                <label className="block text-xs font-semibold text-slate-700 uppercase">
                  Plan Name *
                </label>
                <input
                  type="text"
                  required
                  value={newPlan.name}
                  onChange={(e) => setNewPlan({ ...newPlan, name: e.target.value })}
                  className="mt-1 w-full px-3 py-2 border border-slate-300 rounded-lg text-sm"
                  placeholder="Quarterly Strength & Cardio"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 uppercase">
                  Duration (Days) *
                </label>
                <input
                  type="number"
                  required
                  value={newPlan.duration_days}
                  onChange={(e) =>
                    setNewPlan({ ...newPlan, duration_days: Number(e.target.value) })
                  }
                  className="mt-1 w-full px-3 py-2 border border-slate-300 rounded-lg text-sm"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 uppercase">
                  Price (₹ INR) *
                </label>
                <input
                  type="number"
                  required
                  value={planPriceRupees}
                  onChange={(e) => setPlanPriceRupees(Number(e.target.value))}
                  className="mt-1 w-full px-3 py-2 border border-slate-300 rounded-lg text-sm"
                />
              </div>

              <div className="flex justify-end space-x-3 pt-4 border-t border-slate-200">
                <button
                  type="button"
                  onClick={() => setShowAddPlan(false)}
                  className="px-4 py-2 border border-slate-300 rounded-lg text-sm font-medium text-slate-700 hover:bg-slate-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 bg-indigo-600 text-white rounded-lg text-sm font-semibold hover:bg-indigo-500 shadow-sm"
                >
                  Save Plan
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
