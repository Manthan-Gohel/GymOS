import React, { useEffect, useState } from 'react';
import { api } from '../services/api';
import { MembershipPlan } from '../types/plan';
import {
  CreateEquipmentPayload,
  Equipment,
  Expense,
  MaintenanceSchedule,
  PayrollRecord,
  StaffAttendance,
  StaffAttendanceStatus,
  StaffUser,
  Trainer,
} from '../types/ops';
import {
  AlertTriangle,
  Check,
  Layers,
  Plus,
  RefreshCw,
  Shield,
  ToggleLeft,
  ToggleRight,
  UserCheck,
  Wrench,
} from 'lucide-react';

type Tab = 'plans' | 'trainers' | 'staff' | 'expenses' | 'equipment';

const rupees = (paise: number) => (paise / 100).toFixed(2);
const today = () => new Date().toISOString().slice(0, 10);
const thisMonth = () => new Date().toISOString().slice(0, 7);

const inputClass = 'px-3 py-2 border border-slate-300 rounded-lg text-sm bg-white';

export const AdminPanel: React.FC = () => {
  const [tab, setTab] = useState<Tab>('plans');
  const [error, setError] = useState<string | null>(null);

  const [plans, setPlans] = useState<MembershipPlan[]>([]);
  const [trainers, setTrainers] = useState<Trainer[]>([]);
  const [users, setUsers] = useState<StaffUser[]>([]);
  const [attendance, setAttendance] = useState<StaffAttendance[]>([]);
  const [payroll, setPayroll] = useState<PayrollRecord[]>([]);
  const [expenses, setExpenses] = useState<Expense[]>([]);
  const [equipment, setEquipment] = useState<Equipment[]>([]);
  const [maintenance, setMaintenance] = useState<MaintenanceSchedule[]>([]);

  const [loading, setLoading] = useState(true);

  const [newPlan, setNewPlan] = useState({ name: '', duration_days: 30, rupees: 1500 });
  const [newTrainer, setNewTrainer] = useState({ full_name: '', phone: '', specialty: '' });
  const [slot, setSlot] = useState({ trainer_id: '', weekday: '0', start_time: '06:00', end_time: '10:00' });
  const [assign, setAssign] = useState({ trainer_id: '', member_id: '' });
  const [memberOptions, setMemberOptions] = useState<{ id: number; full_name: string }[]>([]);
  const [attendanceForm, setAttendanceForm] = useState({
    user_id: '',
    on_date: today(),
    status: 'present' as StaffAttendanceStatus,
  });
  const [payrollForm, setPayrollForm] = useState({
    user_id: '',
    month: thisMonth(),
    base_rupees: 20000,
    bonus_rupees: 0,
    deductions_rupees: 0,
  });
  const [expenseForm, setExpenseForm] = useState({
    category: '',
    amount_rupees: 0,
    spent_on: today(),
    vendor: '',
  });
  const [equipmentForm, setEquipmentForm] = useState<CreateEquipmentPayload>({
    name: '',
    category: 'strength',
  });
  const [maintenanceForm, setMaintenanceForm] = useState({
    equipment_id: '',
    title: '',
    due_on: today(),
    interval_days: '',
  });

  const loadAll = async () => {
    setLoading(true);
    const results = await Promise.allSettled([
      api.getPlans(),
      api.getTrainers(),
      api.getUsers(),
      api.getStaffAttendance(),
      api.getPayroll(),
      api.getExpenses(),
      api.getEquipment(),
      api.getMaintenanceDue(),
      api.getMembers(),
    ]);
    const value = <T,>(index: number, fallback: T): T =>
      results[index].status === 'fulfilled' ? (results[index] as PromiseFulfilledResult<T>).value : fallback;
    setPlans(value(0, []));
    setTrainers(value(1, []));
    setUsers(value(2, []));
    setAttendance(value(3, []));
    setPayroll(value(4, []));
    setExpenses(value(5, []));
    setEquipment(value(6, []));
    setMaintenance(value(7, []));
    setMemberOptions(value(8, []).map((m: { id: number; full_name: string }) => ({ id: m.id, full_name: m.full_name })));
    const firstError = results.find((r) => r.status === 'rejected');
    setError(firstError ? (firstError as PromiseRejectedResult).reason.message : null);
    setLoading(false);
  };

  useEffect(() => {
    loadAll();
  }, []);

  const run = async (action: () => Promise<unknown>) => {
    try {
      await action();
      setError(null);
      await loadAll();
    } catch (err) {
      setError((err as Error).message);
    }
  };

  const tabs: [Tab, string][] = [
    ['plans', 'Plans'],
    ['trainers', 'Trainers'],
    ['staff', 'Staff & Payroll'],
    ['expenses', 'Expenses'],
    ['equipment', 'Equipment'],
  ];

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight flex items-center space-x-2">
            <Shield className="w-7 h-7 text-emerald-600" />
            <span>Admin Console</span>
          </h1>
          <p className="text-sm text-slate-500">Plans, trainers, staff records, expenses and equipment</p>
        </div>
        <button
          onClick={loadAll}
          className="p-2 text-slate-500 hover:text-slate-800 hover:bg-slate-100 rounded-lg transition self-start"
          title="Refresh"
        >
          <RefreshCw className="w-4 h-4" />
        </button>
      </div>

      <div className="flex flex-wrap gap-1 border-b border-slate-200">
        {tabs.map(([key, label]) => (
          <button
            key={key}
            onClick={() => setTab(key)}
            className={`px-4 py-2 text-sm font-semibold border-b-2 -mb-px transition ${
              tab === key
                ? 'border-emerald-600 text-emerald-700'
                : 'border-transparent text-slate-500 hover:text-slate-800'
            }`}
          >
            {label}
          </button>
        ))}
      </div>

      {error && (
        <div className="p-4 bg-rose-50 border border-rose-200 rounded-xl text-rose-700 text-sm flex items-center space-x-2">
          <AlertTriangle className="w-5 h-5 flex-shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {loading && <div className="text-sm text-slate-400">Loading…</div>}

      {tab === 'plans' && (
        <section className="space-y-4">
          <form
            onSubmit={(e) => {
              e.preventDefault();
              run(() =>
                api.createPlan({
                  name: newPlan.name,
                  duration_days: Number(newPlan.duration_days),
                  price_paise: Math.round(Number(newPlan.rupees) * 100),
                  currency: 'INR',
                }),
              ).then(() => setNewPlan({ name: '', duration_days: 30, rupees: 1500 }));
            }}
            className="bg-white border border-slate-200 rounded-xl p-4 grid grid-cols-1 sm:grid-cols-4 gap-3 items-end"
          >
            <label className="text-xs font-semibold text-slate-600">
              Name
              <input required value={newPlan.name} onChange={(e) => setNewPlan({ ...newPlan, name: e.target.value })} className={`${inputClass} w-full mt-1`} />
            </label>
            <label className="text-xs font-semibold text-slate-600">
              Duration (days)
              <input required type="number" min={1} value={newPlan.duration_days} onChange={(e) => setNewPlan({ ...newPlan, duration_days: Number(e.target.value) })} className={`${inputClass} w-full mt-1`} />
            </label>
            <label className="text-xs font-semibold text-slate-600">
              Price (₹)
              <input required type="number" min={0} value={newPlan.rupees} onChange={(e) => setNewPlan({ ...newPlan, rupees: Number(e.target.value) })} className={`${inputClass} w-full mt-1`} />
            </label>
            <button type="submit" className="flex items-center justify-center gap-1 px-3 py-2 bg-emerald-600 text-white rounded-lg text-sm font-semibold">
              <Plus className="w-4 h-4" /> Add Plan
            </button>
          </form>

          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
            {plans.map((plan) => (
              <div key={plan.id} className="bg-white border border-slate-200 rounded-xl p-4 space-y-2">
                <div className="flex items-start justify-between">
                  <div>
                    <h3 className="font-semibold text-slate-900 flex items-center gap-2">
                      <Layers className="w-4 h-4 text-emerald-600" />
                      {plan.name}
                    </h3>
                    <p className="text-xs text-slate-500">{plan.duration_days} days · ₹{rupees(plan.price_paise)}</p>
                  </div>
                  <button
                    onClick={() => run(() => api.updatePlan(plan.id, { is_active: !plan.is_active }))}
                    className={`flex items-center gap-1 text-xs font-semibold ${plan.is_active ? 'text-emerald-600' : 'text-slate-400'}`}
                  >
                    {plan.is_active ? <ToggleRight className="w-5 h-5" /> : <ToggleLeft className="w-5 h-5" />}
                    {plan.is_active ? 'Active' : 'Inactive'}
                  </button>
                </div>
                {plan.terms && <p className="text-xs text-slate-500">{plan.terms}</p>}
              </div>
            ))}
            {!loading && plans.length === 0 && <p className="text-sm text-slate-400">No plans yet.</p>}
          </div>
        </section>
      )}

      {tab === 'trainers' && (
        <section className="space-y-4">
          <form
            onSubmit={(e) => {
              e.preventDefault();
              run(() =>
                api.createTrainer({
                  full_name: newTrainer.full_name,
                  phone: newTrainer.phone,
                  specialty: newTrainer.specialty || null,
                }),
              ).then(() => setNewTrainer({ full_name: '', phone: '', specialty: '' }));
            }}
            className="bg-white border border-slate-200 rounded-xl p-4 grid grid-cols-1 sm:grid-cols-4 gap-3 items-end"
          >
            <input required placeholder="Full name" value={newTrainer.full_name} onChange={(e) => setNewTrainer({ ...newTrainer, full_name: e.target.value })} className={inputClass} />
            <input required placeholder="Phone" value={newTrainer.phone} onChange={(e) => setNewTrainer({ ...newTrainer, phone: e.target.value })} className={inputClass} />
            <input placeholder="Specialty" value={newTrainer.specialty} onChange={(e) => setNewTrainer({ ...newTrainer, specialty: e.target.value })} className={inputClass} />
            <button type="submit" className="px-3 py-2 bg-emerald-600 text-white rounded-lg text-sm font-semibold">Add Trainer</button>
          </form>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            {trainers.map((trainer) => (
              <div key={trainer.id} className="bg-white border border-slate-200 rounded-xl p-4 space-y-3">
                <div className="flex items-start justify-between">
                  <div>
                    <h3 className="font-semibold text-slate-900 flex items-center gap-2">
                      <UserCheck className="w-4 h-4 text-emerald-600" />
                      {trainer.full_name}
                    </h3>
                    <p className="text-xs text-slate-500">{trainer.phone} · {trainer.specialty || 'General'}</p>
                  </div>
                  <button
                    onClick={() => run(() => api.updateTrainer(trainer.id, { is_active: !trainer.is_active }))}
                    className={`text-xs font-semibold ${trainer.is_active ? 'text-emerald-600' : 'text-slate-400'}`}
                  >
                    {trainer.is_active ? 'Active' : 'Inactive'}
                  </button>
                </div>

                <form
                  onSubmit={(e) => {
                    e.preventDefault();
                    if (!slot.trainer_id) return;
                    run(() =>
                      api.addTrainerAvailability(Number(slot.trainer_id), {
                        weekday: Number(slot.weekday),
                        start_time: slot.start_time,
                        end_time: slot.end_time,
                      }),
                    );
                  }}
                  className="flex flex-wrap items-center gap-2 text-xs"
                >
                  <select value={slot.trainer_id} onChange={(e) => setSlot({ ...slot, trainer_id: e.target.value })} className={inputClass}>
                    <option value="">Trainer…</option>
                    {trainers.map((t) => (
                      <option key={t.id} value={t.id}>{t.full_name}</option>
                    ))}
                  </select>
                  <select value={slot.weekday} onChange={(e) => setSlot({ ...slot, weekday: e.target.value })} className={inputClass}>
                    {['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'].map((day, index) => (
                      <option key={day} value={index}>{day}</option>
                    ))}
                  </select>
                  <input type="time" value={slot.start_time} onChange={(e) => setSlot({ ...slot, start_time: e.target.value })} className={inputClass} />
                  <input type="time" value={slot.end_time} onChange={(e) => setSlot({ ...slot, end_time: e.target.value })} className={inputClass} />
                  <button type="submit" className="px-2 py-1.5 bg-slate-800 text-white rounded-lg font-semibold">Add Slot</button>
                </form>

                <form
                  onSubmit={(e) => {
                    e.preventDefault();
                    if (!assign.trainer_id || !assign.member_id) return;
                    run(() => api.assignMember(Number(assign.trainer_id), Number(assign.member_id)));
                  }}
                  className="flex flex-wrap items-center gap-2 text-xs"
                >
                  <select value={assign.trainer_id} onChange={(e) => setAssign({ ...assign, trainer_id: e.target.value })} className={inputClass}>
                    <option value="">Trainer…</option>
                    {trainers.map((t) => (
                      <option key={t.id} value={t.id}>{t.full_name}</option>
                    ))}
                  </select>
                  <select value={assign.member_id} onChange={(e) => setAssign({ ...assign, member_id: e.target.value })} className={inputClass}>
                    <option value="">Member…</option>
                    {memberOptions.map((m) => (
                      <option key={m.id} value={m.id}>{m.full_name}</option>
                    ))}
                  </select>
                  <button type="submit" className="px-2 py-1.5 bg-emerald-600 text-white rounded-lg font-semibold">Assign</button>
                </form>
              </div>
            ))}
            {!loading && trainers.length === 0 && <p className="text-sm text-slate-400">No trainers yet.</p>}
          </div>
        </section>
      )}

      {tab === 'staff' && (
        <section className="space-y-4">
          <form
            onSubmit={(e) => {
              e.preventDefault();
              run(() =>
                api.recordStaffAttendance({
                  user_id: Number(attendanceForm.user_id),
                  on_date: attendanceForm.on_date,
                  status: attendanceForm.status,
                }),
              );
            }}
            className="bg-white border border-slate-200 rounded-xl p-4 grid grid-cols-1 sm:grid-cols-4 gap-3 items-end"
          >
            <select required value={attendanceForm.user_id} onChange={(e) => setAttendanceForm({ ...attendanceForm, user_id: e.target.value })} className={inputClass}>
              <option value="">Staff member…</option>
              {users.map((u) => (
                <option key={u.id} value={u.id}>{u.full_name || u.email}</option>
              ))}
            </select>
            <input type="date" required value={attendanceForm.on_date} onChange={(e) => setAttendanceForm({ ...attendanceForm, on_date: e.target.value })} className={inputClass} />
            <select value={attendanceForm.status} onChange={(e) => setAttendanceForm({ ...attendanceForm, status: e.target.value as StaffAttendanceStatus })} className={inputClass}>
              {['present', 'absent', 'half_day', 'leave'].map((status) => (
                <option key={status} value={status}>{status}</option>
              ))}
            </select>
            <button type="submit" className="px-3 py-2 bg-emerald-600 text-white rounded-lg text-sm font-semibold">Record Attendance</button>
          </form>

          <div className="bg-white border border-slate-200 rounded-xl overflow-hidden">
            <table className="w-full text-left text-sm">
              <thead className="bg-slate-50 text-slate-500 text-xs font-semibold uppercase border-b border-slate-200">
                <tr>
                  <th className="px-4 py-2">Staff</th>
                  <th className="px-4 py-2">Date</th>
                  <th className="px-4 py-2">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {attendance.slice(0, 15).map((row) => (
                  <tr key={row.id}>
                    <td className="px-4 py-2">{users.find((u) => u.id === row.user_id)?.full_name || `User #${row.user_id}`}</td>
                    <td className="px-4 py-2 text-xs text-slate-500">{row.on_date}</td>
                    <td className="px-4 py-2 text-xs capitalize">{row.status.replace('_', ' ')}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            {!loading && attendance.length === 0 && <p className="p-6 text-sm text-slate-400">No attendance records.</p>}
          </div>

          <form
            onSubmit={(e) => {
              e.preventDefault();
              run(() =>
                api.createPayroll({
                  user_id: Number(payrollForm.user_id),
                  month: payrollForm.month,
                  base_paise: Math.round(Number(payrollForm.base_rupees) * 100),
                  bonus_paise: Math.round(Number(payrollForm.bonus_rupees) * 100),
                  deductions_paise: Math.round(Number(payrollForm.deductions_rupees) * 100),
                }),
              );
            }}
            className="bg-white border border-slate-200 rounded-xl p-4 grid grid-cols-1 sm:grid-cols-5 gap-3 items-end"
          >
            <select required value={payrollForm.user_id} onChange={(e) => setPayrollForm({ ...payrollForm, user_id: e.target.value })} className={inputClass}>
              <option value="">Staff member…</option>
              {users.map((u) => (
                <option key={u.id} value={u.id}>{u.full_name || u.email}</option>
              ))}
            </select>
            <input type="month" required value={payrollForm.month} onChange={(e) => setPayrollForm({ ...payrollForm, month: e.target.value })} className={inputClass} />
            <input type="number" min={0} required value={payrollForm.base_rupees} onChange={(e) => setPayrollForm({ ...payrollForm, base_rupees: Number(e.target.value) })} className={inputClass} placeholder="Base ₹" />
            <input type="number" min={0} value={payrollForm.bonus_rupees} onChange={(e) => setPayrollForm({ ...payrollForm, bonus_rupees: Number(e.target.value) })} className={inputClass} placeholder="Bonus ₹" />
            <button type="submit" className="px-3 py-2 bg-emerald-600 text-white rounded-lg text-sm font-semibold">Create Payroll</button>
          </form>

          <div className="bg-white border border-slate-200 rounded-xl overflow-hidden">
            <table className="w-full text-left text-sm">
              <thead className="bg-slate-50 text-slate-500 text-xs font-semibold uppercase border-b border-slate-200">
                <tr>
                  <th className="px-4 py-2">Staff</th>
                  <th className="px-4 py-2">Month</th>
                  <th className="px-4 py-2">Net</th>
                  <th className="px-4 py-2">Status</th>
                  <th className="px-4 py-2" />
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {payroll.map((row) => (
                  <tr key={row.id}>
                    <td className="px-4 py-2">{users.find((u) => u.id === row.user_id)?.full_name || `User #${row.user_id}`}</td>
                    <td className="px-4 py-2 text-xs">{row.month}</td>
                    <td className="px-4 py-2">₹{rupees(row.net_paise)}</td>
                    <td className="px-4 py-2 text-xs capitalize">{row.status}</td>
                    <td className="px-4 py-2 text-right">
                      {row.status === 'draft' && (
                        <button
                          onClick={() => run(() => api.finalizePayroll(row.id))}
                          className="text-xs font-semibold text-emerald-600 flex items-center gap-1 justify-end"
                        >
                          <Check className="w-3.5 h-3.5" /> Finalize
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {!loading && payroll.length === 0 && <p className="p-6 text-sm text-slate-400">No payroll records.</p>}
          </div>
        </section>
      )}

      {tab === 'expenses' && (
        <section className="space-y-4">
          <form
            onSubmit={(e) => {
              e.preventDefault();
              run(() =>
                api.createExpense({
                  category: expenseForm.category,
                  amount_paise: Math.round(Number(expenseForm.amount_rupees) * 100),
                  spent_on: expenseForm.spent_on,
                  vendor: expenseForm.vendor || null,
                }),
              );
            }}
            className="bg-white border border-slate-200 rounded-xl p-4 grid grid-cols-1 sm:grid-cols-5 gap-3 items-end"
          >
            <input required placeholder="Category" value={expenseForm.category} onChange={(e) => setExpenseForm({ ...expenseForm, category: e.target.value })} className={inputClass} />
            <input required type="number" min={1} value={expenseForm.amount_rupees} onChange={(e) => setExpenseForm({ ...expenseForm, amount_rupees: Number(e.target.value) })} className={inputClass} placeholder="Amount ₹" />
            <input type="date" required value={expenseForm.spent_on} onChange={(e) => setExpenseForm({ ...expenseForm, spent_on: e.target.value })} className={inputClass} />
            <input placeholder="Vendor" value={expenseForm.vendor} onChange={(e) => setExpenseForm({ ...expenseForm, vendor: e.target.value })} className={inputClass} />
            <button type="submit" className="px-3 py-2 bg-emerald-600 text-white rounded-lg text-sm font-semibold">Add Expense</button>
          </form>

          <div className="bg-white border border-slate-200 rounded-xl overflow-hidden">
            <table className="w-full text-left text-sm">
              <thead className="bg-slate-50 text-slate-500 text-xs font-semibold uppercase border-b border-slate-200">
                <tr>
                  <th className="px-4 py-2">Category</th>
                  <th className="px-4 py-2">Vendor</th>
                  <th className="px-4 py-2">Date</th>
                  <th className="px-4 py-2 text-right">Amount</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {expenses.map((expense) => (
                  <tr key={expense.id}>
                    <td className="px-4 py-2 font-medium">{expense.category}</td>
                    <td className="px-4 py-2 text-xs text-slate-500">{expense.vendor || '—'}</td>
                    <td className="px-4 py-2 text-xs text-slate-500">{expense.spent_on}</td>
                    <td className="px-4 py-2 text-right">₹{rupees(expense.amount_paise)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            {!loading && expenses.length === 0 && <p className="p-6 text-sm text-slate-400">No expenses recorded.</p>}
          </div>
        </section>
      )}

      {tab === 'equipment' && (
        <section className="space-y-4">
          <form
            onSubmit={(e) => {
              e.preventDefault();
              run(() => api.createEquipment(equipmentForm)).then(() =>
                setEquipmentForm({ name: '', category: 'strength' }),
              );
            }}
            className="bg-white border border-slate-200 rounded-xl p-4 grid grid-cols-1 sm:grid-cols-4 gap-3 items-end"
          >
            <input required placeholder="Equipment name" value={equipmentForm.name} onChange={(e) => setEquipmentForm({ ...equipmentForm, name: e.target.value })} className={inputClass} />
            <input required placeholder="Category" value={equipmentForm.category} onChange={(e) => setEquipmentForm({ ...equipmentForm, category: e.target.value })} className={inputClass} />
            <input placeholder="Serial number" value={equipmentForm.serial_number ?? ''} onChange={(e) => setEquipmentForm({ ...equipmentForm, serial_number: e.target.value })} className={inputClass} />
            <button type="submit" className="px-3 py-2 bg-emerald-600 text-white rounded-lg text-sm font-semibold">Add Equipment</button>
          </form>

          <form
            onSubmit={(e) => {
              e.preventDefault();
              if (!maintenanceForm.equipment_id) return;
              run(() =>
                api.scheduleMaintenance(Number(maintenanceForm.equipment_id), {
                  title: maintenanceForm.title,
                  due_on: maintenanceForm.due_on,
                  interval_days: maintenanceForm.interval_days ? Number(maintenanceForm.interval_days) : null,
                }),
              );
            }}
            className="bg-white border border-slate-200 rounded-xl p-4 grid grid-cols-1 sm:grid-cols-5 gap-3 items-end"
          >
            <select required value={maintenanceForm.equipment_id} onChange={(e) => setMaintenanceForm({ ...maintenanceForm, equipment_id: e.target.value })} className={inputClass}>
              <option value="">Equipment…</option>
              {equipment.map((item) => (
                <option key={item.id} value={item.id}>{item.name}</option>
              ))}
            </select>
            <input required placeholder="Task title" value={maintenanceForm.title} onChange={(e) => setMaintenanceForm({ ...maintenanceForm, title: e.target.value })} className={inputClass} />
            <input type="date" required value={maintenanceForm.due_on} onChange={(e) => setMaintenanceForm({ ...maintenanceForm, due_on: e.target.value })} className={inputClass} />
            <input type="number" min={1} placeholder="Every N days" value={maintenanceForm.interval_days} onChange={(e) => setMaintenanceForm({ ...maintenanceForm, interval_days: e.target.value })} className={inputClass} />
            <button type="submit" className="px-3 py-2 bg-slate-800 text-white rounded-lg text-sm font-semibold">Schedule</button>
          </form>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <div className="bg-white border border-slate-200 rounded-xl p-4">
              <h3 className="font-semibold text-slate-800 mb-3 flex items-center gap-2">
                <Wrench className="w-4 h-4 text-emerald-600" /> Equipment
              </h3>
              <ul className="divide-y divide-slate-100 text-sm">
                {equipment.map((item) => (
                  <li key={item.id} className="py-2 flex items-center justify-between gap-2">
                    <div>
                      <div className="font-medium text-slate-900">{item.name}</div>
                      <div className="text-xs text-slate-500">{item.category} · {item.serial_number || 'no serial'}</div>
                    </div>
                    <select
                      value={item.status}
                      onChange={(e) => run(() => api.updateEquipment(item.id, { status: e.target.value as Equipment['status'] }))}
                      className="text-xs border border-slate-200 rounded px-1 py-0.5 bg-white"
                    >
                      {['operational', 'under_maintenance', 'retired'].map((status) => (
                        <option key={status} value={status}>{status.replace('_', ' ')}</option>
                      ))}
                    </select>
                  </li>
                ))}
                {!loading && equipment.length === 0 && <p className="text-sm text-slate-400 py-2">No equipment yet.</p>}
              </ul>
            </div>

            <div className="bg-white border border-slate-200 rounded-xl p-4">
              <h3 className="font-semibold text-slate-800 mb-3">Scheduled maintenance</h3>
              <ul className="divide-y divide-slate-100 text-sm">
                {maintenance.map((schedule) => (
                  <li key={schedule.id} className="py-2 flex items-center justify-between gap-2">
                    <div>
                      <div className="font-medium text-slate-900">{schedule.title}</div>
                      <div className="text-xs text-slate-500">
                        {equipment.find((e) => e.id === schedule.equipment_id)?.name || `Equipment #${schedule.equipment_id}`} · due {schedule.due_on}
                      </div>
                    </div>
                    <button
                      onClick={() => run(() => api.completeMaintenance(schedule.id))}
                      className="text-xs font-semibold text-emerald-600 flex items-center gap-1"
                    >
                      <Check className="w-3.5 h-3.5" /> Done
                    </button>
                  </li>
                ))}
                {!loading && maintenance.length === 0 && <p className="text-sm text-slate-400 py-2">Nothing scheduled.</p>}
              </ul>
            </div>
          </div>
        </section>
      )}
    </div>
  );
};
