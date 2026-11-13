import React, { useState, useEffect } from 'react';
import { api } from '../services/api';
import { Member, CreateMemberPayload } from '../types/member';
import { MembershipPlan, Membership } from '../types/plan';
import { MemberDues } from '../types/payment';
import { LeadsBoard } from '../components/LeadsBoard';
import { ComplaintsBoard } from '../components/ComplaintsBoard';
import {
  Users,
  UserPlus,
  Search,
  CreditCard,
  PlusCircle,
  FileText,
  Phone,
  ShieldCheck,
  CheckCircle2,
  XCircle,
  RefreshCw,
  AlertTriangle,
} from 'lucide-react';

export const ReceptionPanel: React.FC = () => {
  const [members, setMembers] = useState<Member[]>([]);
  const [plans, setPlans] = useState<MembershipPlan[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [tab, setTab] = useState<'members' | 'leads' | 'complaints'>('members');

  // Modals state
  const [showAddMember, setShowAddMember] = useState(false);
  const [showPurchasePlan, setShowPurchasePlan] = useState(false);
  const [showRecordPayment, setShowRecordPayment] = useState(false);
  const [selectedMember, setSelectedMember] = useState<Member | null>(null);
  const [memberDues, setMemberDues] = useState<MemberDues | null>(null);
  const [memberMemberships, setMemberMemberships] = useState<Membership[]>([]);

  // Form states
  const [newMember, setNewMember] = useState<CreateMemberPayload>({
    full_name: '',
    phone: '',
    email: '',
    kyc_id_type: 'Aadhaar',
    kyc_id_number: '',
    emergency_contact_name: '',
    emergency_contact_phone: '',
    health_notes: '',
    whatsapp_consent: true,
  });

  const [selectedPlanId, setSelectedPlanId] = useState<number | ''>('');
  const [paymentAmountRupees, setPaymentAmountRupees] = useState<number | ''>('');
  const [paymentMethod, setPaymentMethod] = useState<'cash' | 'upi' | 'card' | 'mock'>('upi');
  const [paymentReference, setPaymentReference] = useState('');

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [membersData, plansData] = await Promise.all([
        api.getMembers(),
        api.getPlans(),
      ]);
      setMembers(membersData);
      setPlans(plansData.filter((p) => p.is_active));
    } catch (err: any) {
      setError(err.message || 'Failed to load reception data');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleSelectMember = async (member: Member) => {
    setSelectedMember(member);
    try {
      const [dues, memberships] = await Promise.all([
        api.getMemberDues(member.id).catch(() => null),
        api.getMemberships(member.id).catch(() => []),
      ]);
      setMemberDues(dues);
      setMemberMemberships(memberships);
    } catch (e) {
      console.error(e);
    }
  };

  const handleCreateMember = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const created = await api.createMember(newMember);
      setMembers([created, ...members]);
      setShowAddMember(false);
      setNewMember({
        full_name: '',
        phone: '',
        email: '',
        kyc_id_type: 'Aadhaar',
        kyc_id_number: '',
        emergency_contact_name: '',
        emergency_contact_phone: '',
        health_notes: '',
        whatsapp_consent: true,
      });
      handleSelectMember(created);
    } catch (err: any) {
      alert(`Error creating member: ${err.message}`);
    }
  };

  const handlePurchasePlan = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedMember || !selectedPlanId) return;
    try {
      await api.purchaseMembership({
        member_id: selectedMember.id,
        plan_id: Number(selectedPlanId),
        start_date: new Date().toISOString().slice(0, 10),
      });
      setShowPurchasePlan(false);
      handleSelectMember(selectedMember);
      alert('Plan purchased and invoice generated successfully!');
    } catch (err: any) {
      alert(`Error purchasing plan: ${err.message}`);
    }
  };

  const handleRecordPayment = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedMember || !paymentAmountRupees) return;
    try {
      await api.recordPayment({
        member_id: selectedMember.id,
        amount_paise: Math.round(Number(paymentAmountRupees) * 100),
        method: paymentMethod,
        reference: paymentReference || undefined,
      });
      setShowRecordPayment(false);
      setPaymentAmountRupees('');
      setPaymentReference('');
      handleSelectMember(selectedMember);
      alert('Payment recorded successfully!');
    } catch (err: any) {
      alert(`Error recording payment: ${err.message}`);
    }
  };

  const filteredMembers = members.filter(
    (m) =>
      m.full_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      m.phone.includes(searchQuery)
  );

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight flex items-center space-x-2">
            <Users className="w-7 h-7 text-emerald-600" />
            <span>Reception Desk</span>
          </h1>
          <p className="text-sm text-slate-500">
            Staff-entered member records, plan enrolments, payment receipts & dues
          </p>
        </div>

        <div className="flex items-center space-x-3">
          <button
            onClick={loadData}
            className="p-2 text-slate-500 hover:text-slate-800 hover:bg-slate-100 rounded-lg transition"
            title="Refresh"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
          <button
            onClick={() => setShowAddMember(true)}
            className="flex items-center space-x-2 px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg text-sm font-semibold shadow-sm transition"
          >
            <UserPlus className="w-4 h-4" />
            <span>New Member</span>
          </button>
        </div>
      </div>

      {error && (
        <div className="p-4 bg-rose-50 border border-rose-200 rounded-xl text-rose-700 text-sm flex items-center space-x-2">
          <AlertTriangle className="w-5 h-5 flex-shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Tabs */}
      <div className="flex gap-1 border-b border-slate-200">
        {([
          ['members', 'Members & Payments'],
          ['leads', 'Leads & Trials'],
          ['complaints', 'Complaints'],
        ] as const).map(([key, label]) => (
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

      {tab === 'leads' && <LeadsBoard />}
      {tab === 'complaints' && <ComplaintsBoard members={members} />}

      {/* Main Grid: Directory + Member Detail Drawer */}
      {tab === 'members' && (
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left: Member Directory */}
        <div className="lg:col-span-2 bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden flex flex-col">
          <div className="p-4 border-b border-slate-200 bg-slate-50 flex items-center justify-between gap-4">
            <div className="relative flex-1">
              <Search className="w-4 h-4 absolute left-3 top-3 text-slate-400" />
              <input
                type="text"
                placeholder="Search by member name or phone..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full pl-9 pr-4 py-2 bg-white border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500"
              />
            </div>
            <span className="text-xs text-slate-500 whitespace-nowrap font-medium">
              {filteredMembers.length} Members
            </span>
          </div>

          <div className="overflow-x-auto flex-1 min-h-[400px]">
            {loading ? (
              <div className="p-12 text-center text-slate-400 text-sm">Loading members...</div>
            ) : filteredMembers.length === 0 ? (
              <div className="p-12 text-center text-slate-400 text-sm">
                No members found. Click "New Member" to register one.
              </div>
            ) : (
              <table className="w-full text-left text-sm">
                <thead className="bg-slate-50 text-slate-500 text-xs font-semibold uppercase tracking-wider border-b border-slate-200">
                  <tr>
                    <th className="px-4 py-3">Member</th>
                    <th className="px-4 py-3">Contact</th>
                    <th className="px-4 py-3">KYC</th>
                    <th className="px-4 py-3">WhatsApp</th>
                    <th className="px-4 py-3 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {filteredMembers.map((member) => (
                    <tr
                      key={member.id}
                      onClick={() => handleSelectMember(member)}
                      className={`cursor-pointer hover:bg-slate-50 transition ${selectedMember?.id === member.id ? 'bg-emerald-50/60' : ''
                        }`}
                    >
                      <td className="px-4 py-3 font-medium text-slate-900">
                        <div className="flex items-center space-x-2">
                          <div className="w-8 h-8 rounded-full bg-slate-200 text-slate-700 flex items-center justify-center font-bold text-xs uppercase">
                            {member.full_name.charAt(0)}
                          </div>
                          <div>
                            <div>{member.full_name}</div>
                            <div className="text-[11px] text-slate-400">ID #{member.id}</div>
                          </div>
                        </div>
                      </td>
                      <td className="px-4 py-3 text-slate-600">
                        <div className="flex items-center space-x-1">
                          <Phone className="w-3 h-3 text-slate-400" />
                          <span>{member.phone}</span>
                        </div>
                        {member.email && (
                          <div className="text-xs text-slate-400">{member.email}</div>
                        )}
                      </td>
                      <td className="px-4 py-3 text-xs text-slate-500">
                        {member.kyc_id_type ? (
                          <span className="inline-flex items-center space-x-1">
                            <ShieldCheck className="w-3.5 h-3.5 text-emerald-600" />
                            <span>{member.kyc_id_type}</span>
                          </span>
                        ) : (
                          <span className="text-slate-400">Pending</span>
                        )}
                      </td>
                      <td className="px-4 py-3 text-xs">
                        {member.whatsapp_consent && !member.whatsapp_opt_out ? (
                          <span className="inline-flex items-center space-x-1 text-emerald-600">
                            <CheckCircle2 className="w-3.5 h-3.5" />
                            <span>Consented</span>
                          </span>
                        ) : (
                          <span className="inline-flex items-center space-x-1 text-slate-400">
                            <XCircle className="w-3.5 h-3.5" />
                            <span>Opted Out</span>
                          </span>
                        )}
                      </td>
                      <td className="px-4 py-3 text-right">
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            handleSelectMember(member);
                          }}
                          className="text-xs font-semibold text-emerald-600 hover:text-emerald-700"
                        >
                          View & Act
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>

        {/* Right: Selected Member Quick Actions & Ledger */}
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-6 flex flex-col justify-between">
          {selectedMember ? (
            <div className="space-y-6">
              <div className="border-b border-slate-100 pb-4">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-semibold uppercase text-emerald-600 bg-emerald-50 px-2 py-0.5 rounded">
                    Active File
                  </span>
                  <span className="text-xs text-slate-400">Member #{selectedMember.id}</span>
                </div>
                <h3 className="text-xl font-bold text-slate-900 mt-2">
                  {selectedMember.full_name}
                </h3>
                <p className="text-xs text-slate-500">{selectedMember.phone}</p>
                {selectedMember.emergency_contact_name && (
                  <p className="text-xs text-slate-400 mt-1">
                    Emergency: {selectedMember.emergency_contact_name} ({selectedMember.emergency_contact_phone})
                  </p>
                )}
                {selectedMember.health_notes && (
                  <div className="mt-2 text-xs bg-amber-50 text-amber-800 p-2 rounded border border-amber-200">
                    <span className="font-semibold">Health notes:</span> {selectedMember.health_notes}
                  </div>
                )}
              </div>

              {/* Dues & Financial Summary */}
              <div>
                <h4 className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-2">
                  Balance & Dues
                </h4>
                <div className="bg-slate-50 rounded-lg p-3 border border-slate-200 flex justify-between items-center">
                  <div>
                    <div className="text-xs text-slate-500">Outstanding Dues</div>
                    <div className="text-xl font-extrabold text-slate-900">
                      ₹{memberDues ? (memberDues.total_due_paise / 100).toFixed(2) : '0.00'}
                    </div>
                  </div>
                  <button
                    onClick={() => setShowRecordPayment(true)}
                    className="flex items-center space-x-1.5 px-3 py-1.5 bg-emerald-600 text-white rounded-lg text-xs font-semibold hover:bg-emerald-500 transition shadow-sm"
                  >
                    <CreditCard className="w-3.5 h-3.5" />
                    <span>Pay Dues</span>
                  </button>
                </div>
              </div>

              {/* Memberships / Plans */}
              <div>
                <div className="flex items-center justify-between mb-2">
                  <h4 className="text-xs font-bold text-slate-500 uppercase tracking-wider">
                    Membership Enrolment
                  </h4>
                  <button
                    onClick={() => setShowPurchasePlan(true)}
                    className="text-xs text-emerald-600 hover:text-emerald-700 font-semibold flex items-center space-x-1"
                  >
                    <PlusCircle className="w-3.5 h-3.5" />
                    <span>Enroll Plan</span>
                  </button>
                </div>
                {memberMemberships.length === 0 ? (
                  <p className="text-xs text-slate-400 italic">No plan active for this member.</p>
                ) : (
                  <div className="space-y-2 max-h-40 overflow-y-auto">
                    {memberMemberships.map((m) => (
                      <div
                        key={m.id}
                        className="p-2.5 rounded-lg border border-slate-200 bg-slate-50/50 text-xs flex justify-between items-center"
                      >
                        <div>
                          <span className="font-semibold capitalize text-slate-800">
                            Plan #{m.plan_id}
                          </span>
                          <span
                            className={`ml-2 px-1.5 py-0.5 rounded text-[10px] uppercase font-bold ${m.status === 'active'
                              ? 'bg-emerald-100 text-emerald-800'
                              : 'bg-slate-200 text-slate-700'
                              }`}
                          >
                            {m.status}
                          </span>
                          <div className="text-[10px] text-slate-400 mt-0.5">
                            Valid: {m.start_date.substring(0, 10)} to {m.end_date.substring(0, 10)}
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          ) : (
            <div className="h-full flex flex-col items-center justify-center text-center p-6 text-slate-400">
              <FileText className="w-12 h-12 mb-3 text-slate-300 stroke-[1.5]" />
              <p className="font-medium text-slate-600">No Member Selected</p>
              <p className="text-xs mt-1">Select a member from the table to view dues and actions.</p>
            </div>
          )}
        </div>
      </div>
      )}

      {/* MODAL: New Member Registration */}
      {showAddMember && (
        <div className="fixed inset-0 bg-slate-900/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-lg w-full p-6 shadow-2xl border border-slate-200 max-h-[90vh] overflow-y-auto">
            <h3 className="text-lg font-bold text-slate-900 mb-4">Register New Member</h3>
            <form onSubmit={handleCreateMember} className="space-y-4 text-sm">
              <div>
                <label className="block text-xs font-semibold text-slate-700 uppercase">
                  Full Name *
                </label>
                <input
                  type="text"
                  required
                  value={newMember.full_name}
                  onChange={(e) => setNewMember({ ...newMember, full_name: e.target.value })}
                  className="mt-1 w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:ring-2 focus:ring-emerald-500"
                  placeholder="Rahul Sharma"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-slate-700 uppercase">
                    Phone Number *
                  </label>
                  <input
                    type="tel"
                    required
                    value={newMember.phone}
                    onChange={(e) => setNewMember({ ...newMember, phone: e.target.value })}
                    className="mt-1 w-full px-3 py-2 border border-slate-300 rounded-lg text-sm"
                    placeholder="9876543210"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-700 uppercase">
                    Email
                  </label>
                  <input
                    type="email"
                    value={newMember.email || ''}
                    onChange={(e) => setNewMember({ ...newMember, email: e.target.value })}
                    className="mt-1 w-full px-3 py-2 border border-slate-300 rounded-lg text-sm"
                    placeholder="rahul@example.com"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-slate-700 uppercase">
                    KYC ID Type
                  </label>
                  <select
                    value={newMember.kyc_id_type || 'Aadhaar'}
                    onChange={(e) => setNewMember({ ...newMember, kyc_id_type: e.target.value })}
                    className="mt-1 w-full px-3 py-2 border border-slate-300 rounded-lg text-sm"
                  >
                    <option value="Aadhaar">Aadhaar</option>
                    <option value="PAN">PAN</option>
                    <option value="Driving License">Driving License</option>
                    <option value="Passport">Passport</option>
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-700 uppercase">
                    KYC Number
                  </label>
                  <input
                    type="text"
                    value={newMember.kyc_id_number || ''}
                    onChange={(e) => setNewMember({ ...newMember, kyc_id_number: e.target.value })}
                    className="mt-1 w-full px-3 py-2 border border-slate-300 rounded-lg text-sm"
                    placeholder="XXXX-XXXX-XXXX"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-slate-700 uppercase">
                    Emergency Contact Name
                  </label>
                  <input
                    type="text"
                    value={newMember.emergency_contact_name || ''}
                    onChange={(e) =>
                      setNewMember({ ...newMember, emergency_contact_name: e.target.value })
                    }
                    className="mt-1 w-full px-3 py-2 border border-slate-300 rounded-lg text-sm"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-700 uppercase">
                    Emergency Phone
                  </label>
                  <input
                    type="tel"
                    value={newMember.emergency_contact_phone || ''}
                    onChange={(e) =>
                      setNewMember({ ...newMember, emergency_contact_phone: e.target.value })
                    }
                    className="mt-1 w-full px-3 py-2 border border-slate-300 rounded-lg text-sm"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 uppercase">
                  Health Notes / Medical Conditions
                </label>
                <textarea
                  rows={2}
                  value={newMember.health_notes || ''}
                  onChange={(e) => setNewMember({ ...newMember, health_notes: e.target.value })}
                  className="mt-1 w-full px-3 py-2 border border-slate-300 rounded-lg text-sm"
                  placeholder="Asthma, past injuries, allergies..."
                />
              </div>

              <div className="flex items-center space-x-2 pt-2">
                <input
                  type="checkbox"
                  id="whatsappConsent"
                  checked={newMember.whatsapp_consent}
                  onChange={(e) =>
                    setNewMember({ ...newMember, whatsapp_consent: e.target.checked })
                  }
                  className="rounded text-emerald-600 focus:ring-emerald-500 h-4 w-4"
                />
                <label htmlFor="whatsappConsent" className="text-xs text-slate-600">
                  Member consents to receive WhatsApp reminders (welcome, expiry, payment dues)
                </label>
              </div>

              <div className="flex justify-end space-x-3 pt-4 border-t border-slate-200">
                <button
                  type="button"
                  onClick={() => setShowAddMember(false)}
                  className="px-4 py-2 border border-slate-300 rounded-lg text-sm font-medium text-slate-700 hover:bg-slate-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 bg-emerald-600 text-white rounded-lg text-sm font-semibold hover:bg-emerald-500 shadow-sm"
                >
                  Save Member
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* MODAL: Purchase Membership Plan */}
      {showPurchasePlan && selectedMember && (
        <div className="fixed inset-0 bg-slate-900/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-md w-full p-6 shadow-2xl border border-slate-200">
            <h3 className="text-lg font-bold text-slate-900 mb-1">Enroll in Membership Plan</h3>
            <p className="text-xs text-slate-500 mb-4">Member: {selectedMember.full_name}</p>
            <form onSubmit={handlePurchasePlan} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-700 uppercase">
                  Select Plan *
                </label>
                <select
                  required
                  value={selectedPlanId}
                  onChange={(e) => setSelectedPlanId(Number(e.target.value))}
                  className="mt-1 w-full px-3 py-2 border border-slate-300 rounded-lg text-sm"
                >
                  <option value="">-- Choose a plan --</option>
                  {plans.map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.name} ({p.duration_days} days) — ₹{(p.price_paise / 100).toFixed(2)}
                    </option>
                  ))}
                </select>
              </div>

              <div className="flex justify-end space-x-3 pt-4 border-t border-slate-200">
                <button
                  type="button"
                  onClick={() => setShowPurchasePlan(false)}
                  className="px-4 py-2 border border-slate-300 rounded-lg text-sm font-medium text-slate-700 hover:bg-slate-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 bg-emerald-600 text-white rounded-lg text-sm font-semibold hover:bg-emerald-500"
                >
                  Confirm & Invoice
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* MODAL: Record Payment */}
      {showRecordPayment && selectedMember && (
        <div className="fixed inset-0 bg-slate-900/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-md w-full p-6 shadow-2xl border border-slate-200">
            <h3 className="text-lg font-bold text-slate-900 mb-1">Record Payment</h3>
            <p className="text-xs text-slate-500 mb-4">Member: {selectedMember.full_name}</p>
            <form onSubmit={handleRecordPayment} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-700 uppercase">
                  Amount (₹ INR) *
                </label>
                <input
                  type="number"
                  step="0.01"
                  required
                  value={paymentAmountRupees}
                  onChange={(e) => setPaymentAmountRupees(Number(e.target.value))}
                  className="mt-1 w-full px-3 py-2 border border-slate-300 rounded-lg text-sm"
                  placeholder="e.g. 1500"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 uppercase">
                  Payment Method *
                </label>
                <select
                  value={paymentMethod}
                  onChange={(e) => setPaymentMethod(e.target.value as any)}
                  className="mt-1 w-full px-3 py-2 border border-slate-300 rounded-lg text-sm"
                >
                  <option value="upi">UPI / QR</option>
                  <option value="cash">Cash</option>
                  <option value="card">Card (POS)</option>
                  <option value="mock">Mock Gateway</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 uppercase">
                  Transaction / Receipt Ref (Optional)
                </label>
                <input
                  type="text"
                  value={paymentReference}
                  onChange={(e) => setPaymentReference(e.target.value)}
                  className="mt-1 w-full px-3 py-2 border border-slate-300 rounded-lg text-sm"
                  placeholder="UPI Ref ID, receipt #, etc."
                />
              </div>

              <div className="flex justify-end space-x-3 pt-4 border-t border-slate-200">
                <button
                  type="button"
                  onClick={() => setShowRecordPayment(false)}
                  className="px-4 py-2 border border-slate-300 rounded-lg text-sm font-medium text-slate-700 hover:bg-slate-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 bg-emerald-600 text-white rounded-lg text-sm font-semibold hover:bg-emerald-500"
                >
                  Record Payment
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
