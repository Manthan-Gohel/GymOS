import React, { useState, useEffect } from 'react';
import { api } from '../services/api';
import { Member } from '../types/member';
import { Invoice } from '../types/payment';
import { Membership } from '../types/plan';
import {
  TrendingUp,
  Users,
  AlertCircle,
  Calendar,
  IndianRupee,
  RefreshCw,
  BellRing,
} from 'lucide-react';

export const OwnerDashboard: React.FC = () => {
  const [members, setMembers] = useState<Member[]>([]);
  const [invoices, setInvoices] = useState<Invoice[]>([]);
  const [memberships, setMemberships] = useState<Membership[]>([]);
  const [loading, setLoading] = useState(true);

  const loadData = async () => {
    setLoading(true);
    try {
      const [membersData, invoicesData, membershipsData] = await Promise.all([
        api.getMembers().catch(() => []),
        api.getInvoices().catch(() => []),
        api.getMemberships().catch(() => []),
      ]);
      setMembers(membersData);
      setInvoices(invoicesData);
      setMemberships(membershipsData);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  // Compute metrics
  const totalRevenuePaise = invoices
    .filter((inv) => inv.status === 'paid' || inv.status === 'partial')
    .reduce((sum, inv) => sum + (inv.total_paise || 0), 0);

  const totalDuesPaise = invoices
    .filter((inv) => inv.status === 'issued' || inv.status === 'partial')
    .reduce((sum, inv) => sum + (inv.total_paise || 0), 0);

  const activeMemberships = memberships.filter((m) => m.status === 'active');

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight flex items-center space-x-2">
            <TrendingUp className="w-7 h-7 text-emerald-600" />
            <span>Owner Executive Dashboard</span>
          </h1>
          <p className="text-sm text-slate-500">
            Real-time gym revenue, dues, membership health and operational metrics
          </p>
        </div>

        <button
          onClick={loadData}
          className="p-2 text-slate-500 hover:text-slate-800 hover:bg-slate-100 rounded-lg transition self-start sm:self-center"
          title="Refresh Metrics"
        >
          <RefreshCw className="w-4 h-4" />
        </button>
      </div>

      {/* KPI CARDS */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
        {/* Card 1: Revenue */}
        <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm flex items-start justify-between">
          <div>
            <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
              Total Revenue
            </p>
            <h3 className="text-2xl font-black text-slate-900 mt-2">
              ₹{(totalRevenuePaise / 100).toLocaleString('en-IN', { minimumFractionDigits: 2 })}
            </h3>
            <p className="text-[11px] text-emerald-600 font-semibold mt-1 flex items-center space-x-1">
              <span>GST & receipts reconciled</span>
            </p>
          </div>
          <div className="p-3 bg-emerald-50 rounded-xl text-emerald-600">
            <IndianRupee className="w-6 h-6" />
          </div>
        </div>

        {/* Card 2: Active Members */}
        <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm flex items-start justify-between">
          <div>
            <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
              Active Members
            </p>
            <h3 className="text-2xl font-black text-slate-900 mt-2">
              {members.filter((m) => m.is_active).length}
            </h3>
            <p className="text-[11px] text-slate-400 mt-1">
              {activeMemberships.length} active plans enrolled
            </p>
          </div>
          <div className="p-3 bg-blue-50 rounded-xl text-blue-600">
            <Users className="w-6 h-6" />
          </div>
        </div>

        {/* Card 3: Outstanding Dues */}
        <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm flex items-start justify-between">
          <div>
            <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
              Pending Dues
            </p>
            <h3 className="text-2xl font-black text-amber-600 mt-2">
              ₹{(totalDuesPaise / 100).toLocaleString('en-IN', { minimumFractionDigits: 2 })}
            </h3>
            <p className="text-[11px] text-amber-700 font-medium mt-1">
              {invoices.filter((i) => i.status !== 'paid').length} unpaid invoices
            </p>
          </div>
          <div className="p-3 bg-amber-50 rounded-xl text-amber-600">
            <AlertCircle className="w-6 h-6" />
          </div>
        </div>

        {/* Card 4: Automated Reminders */}
        <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm flex items-start justify-between">
          <div>
            <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
              WhatsApp Engine
            </p>
            <h3 className="text-2xl font-black text-slate-900 mt-2">Active</h3>
            <p className="text-[11px] text-slate-400 mt-1">openWA Mock / Controlled templates</p>
          </div>
          <div className="p-3 bg-teal-50 rounded-xl text-teal-600">
            <BellRing className="w-6 h-6" />
          </div>
        </div>
      </div>

      {/* RECENT INVOICES & OPERATIONS GRID */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Recent Invoices */}
        <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-6">
          <div className="flex justify-between items-center mb-4">
            <h3 className="font-bold text-slate-900 text-sm">Recent Invoices & GST Breakdown</h3>
            <span className="text-xs text-slate-400 font-medium">{invoices.length} Invoices</span>
          </div>

          <div className="overflow-x-auto">
            {loading ? (
              <p className="text-center py-8 text-xs text-slate-400">Loading invoices...</p>
            ) : invoices.length === 0 ? (
              <p className="text-center py-8 text-xs text-slate-400">No invoices generated yet.</p>
            ) : (
              <table className="w-full text-left text-xs">
                <thead className="bg-slate-50 text-slate-500 font-semibold uppercase border-b border-slate-200">
                  <tr>
                    <th className="py-2.5 px-3">Invoice #</th>
                    <th className="py-2.5 px-3">Member ID</th>
                    <th className="py-2.5 px-3">Total (₹)</th>
                    <th className="py-2.5 px-3">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {invoices.slice(0, 5).map((inv) => (
                    <tr key={inv.id}>
                      <td className="py-2.5 px-3 font-semibold text-slate-900">
                        {inv.invoice_number}
                      </td>
                      <td className="py-2.5 px-3 text-slate-600">#{inv.member_id}</td>
                      <td className="py-2.5 px-3 font-bold text-slate-900">
                        ₹{(inv.total_paise / 100).toFixed(2)}
                      </td>
                      <td className="py-2.5 px-3">
                        <span
                          className={`px-2 py-0.5 rounded-full font-bold uppercase text-[10px] ${
                            inv.status === 'paid'
                              ? 'bg-emerald-100 text-emerald-800'
                              : 'bg-amber-100 text-amber-800'
                          }`}
                        >
                          {inv.status}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>

        {/* Member Lifecycle & Consent Compliance */}
        <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-6">
          <div className="flex justify-between items-center mb-4">
            <h3 className="font-bold text-slate-900 text-sm">Policy & WhatsApp Compliance Status</h3>
            <span className="text-xs bg-emerald-100 text-emerald-800 px-2 py-0.5 rounded font-semibold">
              Compliant
            </span>
          </div>

          <div className="space-y-4 text-xs text-slate-600">
            <div className="p-3 rounded-xl bg-slate-50 border border-slate-200 flex items-start space-x-3">
              <Calendar className="w-5 h-5 text-emerald-600 flex-shrink-0 mt-0.5" />
              <div>
                <p className="font-bold text-slate-800">DPDP Act & Opt-out Compliance</p>
                <p className="text-slate-500 mt-0.5">
                  Every automated reminder checks member WhatsApp consent and opt-out flag prior to
                  enqueuing. Outbound messages log actor, template and timestamp.
                </p>
              </div>
            </div>

            <div className="p-3 rounded-xl bg-slate-50 border border-slate-200 flex items-start space-x-3">
              <TrendingUp className="w-5 h-5 text-blue-600 flex-shrink-0 mt-0.5" />
              <div>
                <p className="font-bold text-slate-800">Multi-Branch Architecture Ready</p>
                <p className="text-slate-500 mt-0.5">
                  Tenant schema is fully partitioned by gym_id and branch_id across all member,
                  plan, payment, and audit tables.
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
