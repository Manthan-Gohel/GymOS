import React, { useEffect, useState } from 'react';
import { api } from '../services/api';
import { Member } from '../types/member';
import { Invoice, Payment } from '../types/payment';
import { Membership } from '../types/plan';
import { Complaint, DailyDashboard, FinancePeriodSummary, Lead } from '../types/ops';
import {
  AlertCircle,
  Calendar,
  IndianRupee,
  RefreshCw,
  TrendingUp,
  Users,
} from 'lucide-react';

const rupees = (paise: number) => (paise / 100).toLocaleString('en-IN', { maximumFractionDigits: 0 });
const isoDate = (date: Date) => date.toISOString().slice(0, 10);

export const OwnerDashboard: React.FC = () => {
  const [members, setMembers] = useState<Member[]>([]);
  const [invoices, setInvoices] = useState<Invoice[]>([]);
  const [payments, setPayments] = useState<Payment[]>([]);
  const [memberships, setMemberships] = useState<Membership[]>([]);
  const [leads, setLeads] = useState<Lead[]>([]);
  const [complaints, setComplaints] = useState<Complaint[]>([]);
  const [daily, setDaily] = useState<DailyDashboard | null>(null);
  const [monthly, setMonthly] = useState<FinancePeriodSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadData = async () => {
    setLoading(true);
    const now = new Date();
    const from = isoDate(new Date(now.getFullYear(), now.getMonth(), 1));
    const results = await Promise.allSettled([
      api.getMembers(),
      api.getInvoices(),
      api.getPayments(),
      api.getMemberships(),
      api.getLeads(),
      api.getComplaints('open'),
      api.getDailyDashboard(),
      api.getSummaryDashboard(from, isoDate(now)),
    ]);
    const value = <T,>(index: number): T => {
      const result = results[index];
      if (result.status === 'rejected') throw result.reason;
      return result.value as T;
    };
    try {
      setMembers(value<Member[]>(0));
      setInvoices(value<Invoice[]>(1));
      setPayments(value<Payment[]>(2));
      setMemberships(value<Membership[]>(3));
      setLeads(value<Lead[]>(4));
      setComplaints(value<Complaint[]>(5));
      setDaily(value<DailyDashboard>(6));
      setMonthly(value<FinancePeriodSummary>(7));
      setError(null);
    } catch (err) {
      const index = results.findIndex((r) => r.status === 'rejected');
      setError(`${(err as Error).message}${index >= 0 ? ` (section ${index + 1})` : ''}`);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const today = isoDate(new Date());
  const paidTotal = payments.filter((p) => p.status === 'paid').reduce((sum, p) => sum + p.amount_paise, 0);
  const invoicedTotal = invoices
    .filter((inv) => inv.status !== 'cancelled')
    .reduce((sum, inv) => sum + inv.total_paise + inv.late_fee_paise, 0);
  const outstanding = Math.max(invoicedTotal - paidTotal, 0);
  const activeMemberships = memberships.filter((m) => m.status === 'active');
  const soon = new Date();
  soon.setDate(soon.getDate() + 7);
  const expiring = activeMemberships.filter((m) => m.end_date <= isoDate(soon));
  const activeMembers = members.filter((m) => m.is_active).length;
  const openLeads = leads.filter((lead) => lead.status !== 'converted' && lead.status !== 'lost').length;

  const cards = [
    {
      label: 'Revenue Today',
      value: `₹${rupees(daily?.revenue_paise ?? 0)}`,
      hint: `${daily?.payments_count ?? 0} payments`,
      icon: IndianRupee,
      tint: 'text-emerald-600 bg-emerald-50',
    },
    {
      label: 'Profit Today',
      value: `₹${rupees(daily?.profit_paise ?? 0)}`,
      hint: `Expenses ₹${rupees(daily?.expense_paise ?? 0)}`,
      icon: TrendingUp,
      tint: 'text-sky-600 bg-sky-50',
    },
    {
      label: 'Outstanding Dues',
      value: `₹${rupees(outstanding)}`,
      hint: `${invoices.filter((i) => i.status === 'issued' || i.status === 'partial').length} open invoices`,
      icon: AlertCircle,
      tint: 'text-amber-600 bg-amber-50',
    },
    {
      label: 'Active Members',
      value: String(activeMembers),
      hint: `${activeMemberships.length} memberships`,
      icon: Users,
      tint: 'text-violet-600 bg-violet-50',
    },
  ];

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight flex items-center space-x-2">
            <TrendingUp className="w-7 h-7 text-emerald-600" />
            <span>Owner Dashboard</span>
          </h1>
          <p className="text-sm text-slate-500">{today} · revenue, dues, expiries and pipeline</p>
        </div>
        <button
          onClick={loadData}
          className="p-2 text-slate-500 hover:text-slate-800 hover:bg-slate-100 rounded-lg transition self-start"
          title="Refresh"
        >
          <RefreshCw className="w-4 h-4" />
        </button>
      </div>

      {error && (
        <div className="p-4 bg-rose-50 border border-rose-200 rounded-xl text-rose-700 text-sm flex items-center space-x-2">
          <AlertCircle className="w-5 h-5 flex-shrink-0" />
          <span>{error}</span>
        </div>
      )}

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
        {cards.map(({ label, value, hint, icon: Icon, tint }) => (
          <div key={label} className="bg-white rounded-xl border border-slate-200 shadow-sm p-5">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold uppercase tracking-wider text-slate-500">{label}</span>
              <span className={`p-2 rounded-lg ${tint}`}>
                <Icon className="w-4 h-4" />
              </span>
            </div>
            <div className="mt-3 text-2xl font-extrabold text-slate-900">{loading ? '—' : value}</div>
            <div className="text-xs text-slate-500 mt-1">{hint}</div>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-5">
          <h2 className="font-semibold text-slate-800 mb-3">This month</h2>
          <dl className="space-y-2 text-sm">
            <div className="flex justify-between"><dt className="text-slate-500">Revenue</dt><dd className="font-semibold">₹{rupees(monthly?.revenue_paise ?? 0)}</dd></div>
            <div className="flex justify-between"><dt className="text-slate-500">Expenses</dt><dd className="font-semibold">₹{rupees(monthly?.expense_paise ?? 0)}</dd></div>
            <div className="flex justify-between border-t border-slate-100 pt-2"><dt className="text-slate-500">Profit</dt><dd className="font-bold text-emerald-700">₹{rupees(monthly?.profit_paise ?? 0)}</dd></div>
            <div className="flex justify-between"><dt className="text-slate-500">Payments</dt><dd className="font-semibold">{monthly?.payments_count ?? 0}</dd></div>
          </dl>
        </div>

        <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-5">
          <h2 className="font-semibold text-slate-800 mb-3 flex items-center gap-2">
            <Calendar className="w-4 h-4 text-amber-500" /> Expiring in 7 days
          </h2>
          {expiring.length === 0 ? (
            <p className="text-sm text-slate-400">No memberships expiring this week.</p>
          ) : (
            <ul className="space-y-2 text-sm">
              {expiring.slice(0, 6).map((membership) => (
                <li key={membership.id} className="flex justify-between gap-2">
                  <span className="text-slate-700">
                    {members.find((m) => m.id === membership.member_id)?.full_name || `Member #${membership.member_id}`}
                  </span>
                  <span className="text-xs text-slate-500">{membership.end_date}</span>
                </li>
              ))}
            </ul>
          )}
        </div>

        <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-5">
          <h2 className="font-semibold text-slate-800 mb-3">Pipeline & complaints</h2>
          <dl className="space-y-2 text-sm">
            <div className="flex justify-between"><dt className="text-slate-500">Open leads</dt><dd className="font-semibold">{openLeads}</dd></div>
            <div className="flex justify-between"><dt className="text-slate-500">Trials booked</dt><dd className="font-semibold">{leads.filter((l) => l.status === 'trial_booked').length}</dd></div>
            <div className="flex justify-between"><dt className="text-slate-500">Converted</dt><dd className="font-semibold">{leads.filter((l) => l.status === 'converted').length}</dd></div>
            <div className="flex justify-between border-t border-slate-100 pt-2"><dt className="text-slate-500">Open complaints</dt><dd className="font-semibold text-rose-600">{complaints.length}</dd></div>
          </dl>
        </div>
      </div>
    </div>
  );
};
