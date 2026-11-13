import { LoginRequest, LoginResponse, User } from '../types/auth';
import { CreateMemberPayload, Member, UpdateMemberPayload } from '../types/member';
import {
  CreatePlanPayload,
  Membership,
  MembershipPlan,
  PurchaseMembershipPayload,
} from '../types/plan';
import {
  Invoice,
  MemberDues,
  Payment,
  PaymentResult,
  RecordPaymentPayload,
} from '../types/payment';
import {
  Complaint,
  ComplaintStatus,
  CreateComplaintPayload,
  CreateEquipmentPayload,
  CreateExpensePayload,
  CreateLeadPayload,
  CreateMaintenancePayload,
  CreateSessionPayload,
  CreateTrainerPayload,
  DailyDashboard,
  Equipment,
  Expense,
  FinancePeriodSummary,
  Lead,
  LeadStatus,
  MaintenanceSchedule,
  PayrollRecord,
  StaffAttendance,
  StaffAttendanceStatus,
  StaffUser,
  Trainer,
  TrainerAssignment,
  TrainerAttendance,
  TrainerAvailability,
  TrainingSession,
} from '../types/ops';

/** Shape returned by every list endpoint except /plans. */
export interface Paginated<T> {
  items: T[];
  total: number;
}

const BASE_URL = '';

class ApiService {
  // VULN-008: token lives in memory only — the HttpOnly cookie authenticates across reloads.
  private token: string | null = null;

  setToken(t: string | null): void {
    this.token = t;
  }

  async logout(): Promise<void> {
    try {
      await this.request<void>('/auth/logout', { method: 'POST' });
    } finally {
      this.token = null;
    }
  }

  private async request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      ...(options.headers as Record<string, string>),
    };

    if (this.token) {
      headers['Authorization'] = `Bearer ${this.token}`;
    }

    const response = await fetch(`${BASE_URL}${endpoint}`, { ...options, headers, credentials: 'include' });

    if (!response.ok) {
      let errorMessage = 'Request failed';
      try {
        const errorData = await response.json();
        const detail = errorData.detail;
        errorMessage =
          typeof detail === 'string'
            ? detail
            : Array.isArray(detail)
              ? detail.map((item: { msg?: string }) => item.msg ?? '').join(', ')
              : errorData.message || errorMessage;
      } catch {
        errorMessage = response.statusText;
      }
      throw new Error(errorMessage);
    }

    if (response.status === 204) {
      return undefined as T;
    }
    return response.json() as Promise<T>;
  }

  /** Unwraps `{items,total}` list payloads into a plain array. */
  private async list<T>(endpoint: string): Promise<T[]> {
    const data = await this.request<Paginated<T>>(endpoint);
    return data.items;
  }

  private post<T>(endpoint: string, body?: unknown): Promise<T> {
    return this.request<T>(endpoint, {
      method: 'POST',
      body: body === undefined ? undefined : JSON.stringify(body),
    });
  }

  private patch<T>(endpoint: string, body: unknown): Promise<T> {
    return this.request<T>(endpoint, { method: 'PATCH', body: JSON.stringify(body) });
  }

  // Auth endpoints
  async login(payload: LoginRequest): Promise<LoginResponse> {
    return this.post<LoginResponse>('/auth/login', payload);
  }

  async getMe(): Promise<User> {
    return this.request<User>('/auth/me');
  }

  // Staff users (owner/admin only)
  async getUsers(): Promise<StaffUser[]> {
    return this.list<StaffUser>('/users');
  }

  // Members endpoints
  async getMembers(): Promise<Member[]> {
    return this.list<Member>('/members');
  }

  async getMember(id: number): Promise<Member> {
    return this.request<Member>(`/members/${id}`);
  }

  async createMember(payload: CreateMemberPayload): Promise<Member> {
    return this.post<Member>('/members', payload);
  }

  async updateMember(id: number, payload: UpdateMemberPayload): Promise<Member> {
    return this.patch<Member>(`/members/${id}`, payload);
  }

  // Plans endpoints
  async getPlans(): Promise<MembershipPlan[]> {
    return this.request<MembershipPlan[]>('/plans');
  }

  async createPlan(payload: CreatePlanPayload): Promise<MembershipPlan> {
    return this.post<MembershipPlan>('/plans', payload);
  }

  async updatePlan(id: number, payload: Partial<CreatePlanPayload>): Promise<MembershipPlan> {
    return this.patch<MembershipPlan>(`/plans/${id}`, payload);
  }

  // Membership lifecycle endpoints
  async getMemberships(memberId?: number): Promise<Membership[]> {
    const url = memberId ? `/memberships?member_id=${memberId}` : '/memberships';
    return this.list<Membership>(url);
  }

  async purchaseMembership(payload: PurchaseMembershipPayload): Promise<Membership> {
    return this.post<Membership>('/memberships/purchase', payload);
  }

  async freezeMembership(id: number, frozenOn: string): Promise<Membership> {
    return this.post<Membership>(`/memberships/${id}/freeze`, { frozen_on: frozenOn });
  }

  async unfreezeMembership(id: number, unfrozenOn: string): Promise<Membership> {
    return this.post<Membership>(`/memberships/${id}/unfreeze`, { unfrozen_on: unfrozenOn });
  }

  async upgradeMembership(
    id: number,
    newPlanId: number,
    startDate?: string,
  ): Promise<{ old_membership: Membership; new_membership: Membership }> {
    return this.post(`/memberships/${id}/upgrade`, {
      new_plan_id: newPlanId,
      start_date: startDate,
    });
  }

  // Invoices & Payments endpoints
  async getInvoices(): Promise<Invoice[]> {
    return this.list<Invoice>('/invoices');
  }

  async getInvoice(id: number): Promise<Invoice> {
    return this.request<Invoice>(`/invoices/${id}`);
  }

  async getPayments(memberId?: number): Promise<Payment[]> {
    const url = memberId ? `/payments?member_id=${memberId}` : '/payments';
    return this.list<Payment>(url);
  }

  async recordPayment(payload: RecordPaymentPayload): Promise<PaymentResult> {
    return this.post<PaymentResult>('/payments', payload);
  }

  async getMemberDues(memberId: number): Promise<MemberDues> {
    return this.request<MemberDues>(`/payments/dues?member_id=${memberId}`);
  }

  // Leads
  async getLeads(status?: LeadStatus): Promise<Lead[]> {
    return this.list<Lead>(status ? `/leads?status=${status}` : '/leads');
  }

  async createLead(payload: CreateLeadPayload): Promise<Lead> {
    return this.post<Lead>('/leads', payload);
  }

  async updateLead(id: number, payload: Partial<CreateLeadPayload> & { status?: LeadStatus }): Promise<Lead> {
    return this.patch<Lead>(`/leads/${id}`, payload);
  }

  // Complaints
  async getComplaints(status?: ComplaintStatus): Promise<Complaint[]> {
    return this.list<Complaint>(status ? `/complaints?status=${status}` : '/complaints');
  }

  async createComplaint(payload: CreateComplaintPayload): Promise<Complaint> {
    return this.post<Complaint>('/complaints', payload);
  }

  async updateComplaint(
    id: number,
    payload: { status?: ComplaintStatus; assigned_to?: number; resolution_notes?: string },
  ): Promise<Complaint> {
    return this.patch<Complaint>(`/complaints/${id}`, payload);
  }

  // Equipment & maintenance
  async getEquipment(): Promise<Equipment[]> {
    return this.list<Equipment>('/equipment');
  }

  async createEquipment(payload: CreateEquipmentPayload): Promise<Equipment> {
    return this.post<Equipment>('/equipment', payload);
  }

  async updateEquipment(id: number, payload: Partial<CreateEquipmentPayload> & { status?: Equipment['status'] }): Promise<Equipment> {
    return this.patch<Equipment>(`/equipment/${id}`, payload);
  }

  async getMaintenanceDue(includeAll = false): Promise<MaintenanceSchedule[]> {
    return this.list<MaintenanceSchedule>(includeAll ? '/maintenance' : '/maintenance?status=scheduled');
  }

  async scheduleMaintenance(equipmentId: number, payload: CreateMaintenancePayload): Promise<MaintenanceSchedule> {
    return this.post<MaintenanceSchedule>(`/equipment/${equipmentId}/maintenance`, payload);
  }

  async completeMaintenance(
    scheduleId: number,
    payload: { completed_on?: string; notes?: string } = {},
  ): Promise<MaintenanceSchedule & { next_schedule_id: number | null }> {
    return this.post(`/maintenance/${scheduleId}/complete`, payload);
  }

  async runMaintenanceReminders(today?: string): Promise<{ sent: number; failed: number; total: number }> {
    return this.post('/maintenance/run-reminders', { today: today });
  }

  // Trainers
  async getTrainers(): Promise<Trainer[]> {
    return this.list<Trainer>('/trainers');
  }

  async createTrainer(payload: CreateTrainerPayload): Promise<Trainer> {
    return this.post<Trainer>('/trainers', payload);
  }

  async updateTrainer(id: number, payload: Partial<CreateTrainerPayload>): Promise<Trainer> {
    return this.patch<Trainer>(`/trainers/${id}`, payload);
  }

  async getTrainerAvailability(id: number): Promise<TrainerAvailability[]> {
    return this.list<TrainerAvailability>(`/trainers/${id}/availability`);
  }

  async addTrainerAvailability(
    id: number,
    payload: { weekday: number; start_time: string; end_time: string },
  ): Promise<TrainerAvailability> {
    return this.post<TrainerAvailability>(`/trainers/${id}/availability`, payload);
  }

  async deleteTrainerAvailability(id: number, slotId: number): Promise<void> {
    return this.request<void>(`/trainers/${id}/availability/${slotId}`, { method: 'DELETE' });
  }

  async getTrainerMembers(id: number): Promise<TrainerAssignment[]> {
    return this.list<TrainerAssignment>(`/trainers/${id}/members`);
  }

  async assignMember(trainerId: number, memberId: number): Promise<TrainerAssignment> {
    return this.post<TrainerAssignment>(`/trainers/${trainerId}/assign`, { member_id: memberId });
  }

  async unassignMember(trainerId: number, memberId: number): Promise<void> {
    return this.request<void>(`/trainers/${trainerId}/assign/${memberId}`, { method: 'DELETE' });
  }

  // Training sessions
  async getSessions(params: { trainer_id?: number; member_id?: number; on_date?: string } = {}): Promise<TrainingSession[]> {
    const query = new URLSearchParams();
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined) query.set(key, String(value));
    });
    const suffix = query.toString() ? `?${query.toString()}` : '';
    return this.list<TrainingSession>(`/sessions${suffix}`);
  }

  async createSession(payload: CreateSessionPayload): Promise<TrainingSession> {
    return this.post<TrainingSession>('/sessions', payload);
  }

  async cancelSession(id: number): Promise<TrainingSession> {
    return this.post<TrainingSession>(`/sessions/${id}/cancel`);
  }

  async recordTrainerAttendance(
    sessionId: number,
    payload: { checked_in_at: string; checked_out_at?: string; notes?: string },
  ): Promise<TrainerAttendance> {
    return this.post<TrainerAttendance>(`/sessions/${sessionId}/attendance`, payload);
  }

  // Staff attendance & payroll (owner/admin)
  async getStaffAttendance(params: { user_id?: number; month?: string } = {}): Promise<StaffAttendance[]> {
    const query = new URLSearchParams();
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined) query.set(key, String(value));
    });
    const suffix = query.toString() ? `?${query.toString()}` : '';
    return this.list<StaffAttendance>(`/staff-attendance${suffix}`);
  }

  async recordStaffAttendance(payload: {
    user_id: number;
    on_date: string;
    status: StaffAttendanceStatus;
    check_in?: string;
    check_out?: string;
    notes?: string;
  }): Promise<StaffAttendance> {
    return this.post<StaffAttendance>('/staff-attendance', payload);
  }

  async getPayroll(params: { month?: string; user_id?: number } = {}): Promise<PayrollRecord[]> {
    const query = new URLSearchParams();
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined) query.set(key, String(value));
    });
    const suffix = query.toString() ? `?${query.toString()}` : '';
    return this.list<PayrollRecord>(`/payroll${suffix}`);
  }

  async createPayroll(payload: {
    user_id: number;
    month: string;
    base_paise: number;
    bonus_paise?: number;
    deductions_paise?: number;
    notes?: string;
  }): Promise<PayrollRecord> {
    return this.post<PayrollRecord>('/payroll', payload);
  }

  async finalizePayroll(id: number): Promise<PayrollRecord> {
    return this.post<PayrollRecord>(`/payroll/${id}/finalize`);
  }

  // Finance (owner/admin)
  async getExpenses(): Promise<Expense[]> {
    return this.list<Expense>('/expenses');
  }

  async createExpense(payload: CreateExpensePayload): Promise<Expense> {
    return this.post<Expense>('/expenses', payload);
  }

  async getDailyDashboard(onDate?: string): Promise<DailyDashboard> {
    return this.request<DailyDashboard>(`/dashboard/daily${onDate ? `?on_date=${onDate}` : ''}`);
  }

  async getSummaryDashboard(fromDate: string, toDate: string): Promise<FinancePeriodSummary> {
    return this.request<FinancePeriodSummary>(
      `/dashboard/summary?from_date=${fromDate}&to_date=${toDate}`,
    );
  }
}

export const api = new ApiService();
