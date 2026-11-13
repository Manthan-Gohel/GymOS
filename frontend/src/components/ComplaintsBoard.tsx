import React, { useEffect, useState } from 'react';
import { api } from '../services/api';
import { Member } from '../types/member';
import { Complaint, ComplaintStatus } from '../types/ops';
import { AlertTriangle, MessageSquareWarning, Plus, RefreshCw } from 'lucide-react';

const STATUSES: ComplaintStatus[] = ['open', 'in_progress', 'resolved', 'closed'];

const STATUS_STYLE: Record<ComplaintStatus, string> = {
  open: 'bg-rose-100 text-rose-800',
  in_progress: 'bg-amber-100 text-amber-800',
  resolved: 'bg-emerald-100 text-emerald-800',
  closed: 'bg-slate-200 text-slate-600',
};

interface Props {
  members: Member[];
}

export const ComplaintsBoard: React.FC<Props> = ({ members }) => {
  const [complaints, setComplaints] = useState<Complaint[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ category: '', description: '', member_id: '' });
  const [resolving, setResolving] = useState<number | null>(null);
  const [resolutionNotes, setResolutionNotes] = useState('');

  const load = async () => {
    setLoading(true);
    try {
      setComplaints(await api.getComplaints());
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
      await api.createComplaint({
        category: form.category,
        description: form.description,
        member_id: form.member_id ? Number(form.member_id) : null,
      });
      setForm({ category: '', description: '', member_id: '' });
      setShowForm(false);
      await load();
    } catch (err) {
      setError((err as Error).message);
    }
  };

  const updateStatus = async (complaint: Complaint, status: ComplaintStatus) => {
    if (status === 'resolved' || status === 'closed') {
      setResolving(complaint.id);
      setResolutionNotes(complaint.resolution_notes ?? '');
      return;
    }
    try {
      const updated = await api.updateComplaint(complaint.id, { status });
      setComplaints((current) => current.map((item) => (item.id === updated.id ? updated : item)));
    } catch (err) {
      setError((err as Error).message);
    }
  };

  const saveResolution = async (complaint: Complaint, status: ComplaintStatus) => {
    try {
      const updated = await api.updateComplaint(complaint.id, {
        status,
        resolution_notes: resolutionNotes.trim(),
      });
      setComplaints((current) => current.map((item) => (item.id === updated.id ? updated : item)));
      setResolving(null);
      setResolutionNotes('');
    } catch (err) {
      setError((err as Error).message);
    }
  };

  const memberName = (id: number | null) => members.find((m) => m.id === id)?.full_name ?? 'Walk-in';

  return (
    <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
      <div className="p-4 border-b border-slate-200 bg-slate-50 flex items-center justify-between">
        <h2 className="font-semibold text-slate-800 flex items-center gap-2">
          <MessageSquareWarning className="w-4 h-4 text-emerald-600" />
          <span>Complaints</span>
          <span className="text-xs font-normal text-slate-500">({complaints.length})</span>
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
            <span>Log Complaint</span>
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
            placeholder="Category (equipment, noise, staff...)"
            value={form.category}
            onChange={(e) => setForm({ ...form, category: e.target.value })}
            className="px-3 py-2 border border-slate-300 rounded-lg text-sm"
          />
          <select
            value={form.member_id}
            onChange={(e) => setForm({ ...form, member_id: e.target.value })}
            className="px-3 py-2 border border-slate-300 rounded-lg text-sm"
          >
            <option value="">Walk-in / no member</option>
            {members.map((member) => (
              <option key={member.id} value={member.id}>
                {member.full_name} ({member.phone})
              </option>
            ))}
          </select>
          <textarea
            required
            placeholder="What happened?"
            value={form.description}
            onChange={(e) => setForm({ ...form, description: e.target.value })}
            className="px-3 py-2 border border-slate-300 rounded-lg text-sm sm:col-span-2"
            rows={3}
          />
          <div className="sm:col-span-2 flex justify-end gap-2">
            <button type="button" onClick={() => setShowForm(false)} className="px-3 py-1.5 text-xs font-semibold text-slate-600">
              Cancel
            </button>
            <button type="submit" className="px-3 py-1.5 bg-emerald-600 text-white rounded-lg text-xs font-semibold">
              Save Complaint
            </button>
          </div>
        </form>
      )}

      {loading ? (
        <div className="p-10 text-center text-sm text-slate-400">Loading complaints...</div>
      ) : complaints.length === 0 ? (
        <div className="p-10 text-center text-sm text-slate-400">No complaints logged.</div>
      ) : (
        <ul className="divide-y divide-slate-100">
          {complaints.map((complaint) => (
            <li key={complaint.id} className="p-4 space-y-2">
              <div className="flex flex-wrap items-start justify-between gap-2">
                <div>
                  <div className="text-sm font-semibold text-slate-900">
                    {complaint.category} · {memberName(complaint.member_id)}
                  </div>
                  <p className="text-sm text-slate-600">{complaint.description}</p>
                  {complaint.resolution_notes && (
                    <p className="text-xs text-emerald-700 mt-1">Resolution: {complaint.resolution_notes}</p>
                  )}
                </div>
                <div className="flex items-center gap-2">
                  <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase ${STATUS_STYLE[complaint.status]}`}>
                    {complaint.status.replace('_', ' ')}
                  </span>
                  <select
                    value={complaint.status}
                    onChange={(e) => updateStatus(complaint, e.target.value as ComplaintStatus)}
                    className="text-xs border border-slate-200 rounded px-1 py-0.5 bg-white"
                    aria-label={`Update status for ${complaint.category}`}
                  >
                    {STATUSES.map((status) => (
                      <option key={status} value={status}>
                        {status.replace('_', ' ')}
                      </option>
                    ))}
                  </select>
                </div>
              </div>
              {resolving === complaint.id && (
                <div className="flex flex-col sm:flex-row gap-2">
                  <input
                    value={resolutionNotes}
                    onChange={(e) => setResolutionNotes(e.target.value)}
                    placeholder="Resolution notes (required)"
                    className="flex-1 px-3 py-1.5 border border-slate-300 rounded-lg text-xs"
                  />
                  <button
                    onClick={() => saveResolution(complaint, complaint.status === 'closed' ? 'closed' : 'resolved')}
                    disabled={!resolutionNotes.trim()}
                    className="px-3 py-1.5 bg-emerald-600 text-white rounded-lg text-xs font-semibold disabled:opacity-50"
                  >
                    Save
                  </button>
                  <button
                    onClick={() => setResolving(null)}
                    className="px-3 py-1.5 text-slate-600 rounded-lg text-xs font-semibold"
                  >
                    Cancel
                  </button>
                </div>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
};
