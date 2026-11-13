import React, { useEffect, useState } from 'react';
import { api } from '../services/api';
import { CreateLeadPayload, Lead, LeadStatus } from '../types/ops';
import { AlertTriangle, Plus, RefreshCw, Target } from 'lucide-react';

const STATUSES: LeadStatus[] = ['new', 'contacted', 'trial_booked', 'converted', 'lost'];

const STATUS_STYLE: Record<LeadStatus, string> = {
  new: 'bg-sky-100 text-sky-800',
  contacted: 'bg-amber-100 text-amber-800',
  trial_booked: 'bg-violet-100 text-violet-800',
  converted: 'bg-emerald-100 text-emerald-800',
  lost: 'bg-slate-200 text-slate-600',
};

const emptyForm: CreateLeadPayload = { full_name: '', phone: '', source: '', trial_date: '', notes: '' };

export const LeadsBoard: React.FC = () => {
  const [leads, setLeads] = useState<Lead[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState<CreateLeadPayload>(emptyForm);

  const load = async () => {
    setLoading(true);
    try {
      setLeads(await api.getLeads());
      setError(null);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const create = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await api.createLead({
        ...form,
        source: form.source || null,
        trial_date: form.trial_date || null,
        notes: form.notes || null,
      });
      setForm(emptyForm);
      setShowForm(false);
      await load();
    } catch (err) {
      setError((err as Error).message);
    }
  };

  const setStatus = async (lead: Lead, status: LeadStatus) => {
    try {
      const updated = await api.updateLead(lead.id, { status });
      setLeads((current) => current.map((item) => (item.id === updated.id ? updated : item)));
    } catch (err) {
      setError((err as Error).message);
    }
  };

  return (
    <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
      <div className="p-4 border-b border-slate-200 bg-slate-50 flex items-center justify-between">
        <h2 className="font-semibold text-slate-800 flex items-center gap-2">
          <Target className="w-4 h-4 text-emerald-600" />
          <span>Leads & Trials</span>
          <span className="text-xs font-normal text-slate-500">({leads.length})</span>
        </h2>
        <div className="flex items-center gap-2">
          <button onClick={load} className="p-2 text-slate-500 hover:bg-slate-100 rounded-lg" title="Refresh">
            <RefreshCw className="w-4 h-4" />
          </button>
          <button
            onClick={() => setShowForm((v) => !v)}
            className="flex items-center gap-1 px-3 py-1.5 bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg text-xs font-semibold"
          >
            <Plus className="w-3.5 h-3.5" />
            <span>Add Lead</span>
          </button>
        </div>
      </div>

      {error && (
        <div className="m-4 p-3 bg-rose-50 border border-rose-200 rounded-lg text-rose-700 text-sm flex gap-2">
          <AlertTriangle className="w-4 h-4 flex-shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {showForm && (
        <form onSubmit={create} className="p-4 border-b border-slate-200 grid grid-cols-1 sm:grid-cols-2 gap-3 bg-slate-50/60">
          <input
            required
            placeholder="Full name"
            value={form.full_name}
            onChange={(e) => setForm({ ...form, full_name: e.target.value })}
            className="px-3 py-2 border border-slate-300 rounded-lg text-sm"
          />
          <input
            required
            placeholder="Phone"
            value={form.phone}
            onChange={(e) => setForm({ ...form, phone: e.target.value })}
            className="px-3 py-2 border border-slate-300 rounded-lg text-sm"
          />
          <input
            placeholder="Source (walk-in, Instagram...)"
            value={form.source ?? ''}
            onChange={(e) => setForm({ ...form, source: e.target.value })}
            className="px-3 py-2 border border-slate-300 rounded-lg text-sm"
          />
          <input
            type="date"
            value={form.trial_date ?? ''}
            onChange={(e) => setForm({ ...form, trial_date: e.target.value })}
            className="px-3 py-2 border border-slate-300 rounded-lg text-sm"
          />
          <input
            placeholder="Notes"
            value={form.notes ?? ''}
            onChange={(e) => setForm({ ...form, notes: e.target.value })}
            className="px-3 py-2 border border-slate-300 rounded-lg text-sm sm:col-span-2"
          />
          <div className="sm:col-span-2 flex justify-end gap-2">
            <button type="button" onClick={() => setShowForm(false)} className="px-3 py-1.5 text-xs font-semibold text-slate-600">
              Cancel
            </button>
            <button type="submit" className="px-3 py-1.5 bg-emerald-600 text-white rounded-lg text-xs font-semibold">
              Save Lead
            </button>
          </div>
        </form>
      )}

      {loading ? (
        <div className="p-10 text-center text-sm text-slate-400">Loading leads...</div>
      ) : leads.length === 0 ? (
        <div className="p-10 text-center text-sm text-slate-400">No leads yet.</div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="bg-slate-50 text-slate-500 text-xs font-semibold uppercase tracking-wider border-b border-slate-200">
              <tr>
                <th className="px-4 py-3">Lead</th>
                <th className="px-4 py-3">Source</th>
                <th className="px-4 py-3">Trial</th>
                <th className="px-4 py-3">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {leads.map((lead) => (
                <tr key={lead.id} className="hover:bg-slate-50">
                  <td className="px-4 py-3">
                    <div className="font-medium text-slate-900">{lead.full_name}</div>
                    <div className="text-xs text-slate-500">{lead.phone}</div>
                  </td>
                  <td className="px-4 py-3 text-xs text-slate-500">{lead.source || '—'}</td>
                  <td className="px-4 py-3 text-xs text-slate-500">{lead.trial_date || '—'}</td>
                  <td className="px-4 py-3">
                    <div className="flex flex-wrap items-center gap-1">
                      <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase ${STATUS_STYLE[lead.status]}`}>
                        {lead.status.replace('_', ' ')}
                      </span>
                      <select
                        value={lead.status}
                        onChange={(e) => setStatus(lead, e.target.value as LeadStatus)}
                        className="text-xs border border-slate-200 rounded px-1 py-0.5 bg-white"
                        aria-label={`Update status for ${lead.full_name}`}
                      >
                        {STATUSES.map((status) => (
                          <option key={status} value={status}>
                            {status.replace('_', ' ')}
                          </option>
                        ))}
                      </select>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};
