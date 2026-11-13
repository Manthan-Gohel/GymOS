import type { UserRole } from './auth';

export interface StaffUser {
  id: number;
  email: string;
  full_name: string;
  branch_id: number | null;
  is_active: boolean;
  roles: UserRole[];
}

export type LeadStatus = 'new' | 'contacted' | 'trial_booked' | 'converted' | 'lost';export interface Lead {
  id: number;
  gym_id: number;
  branch_id: number | null;
  full_name: string;
  phone: string;
  email: string | null;
  source: string | null;
  status: LeadStatus;
  trial_date: string | null;
  assigned_to: number | null;
  notes: string | null;
  created_at: string;
}

export interface CreateLeadPayload {
  full_name: string;
  phone: string;
  email?: string | null;
  source?: string | null;
  notes?: string | null;
  trial_date?: string | null;
  assigned_to?: number | null;
}

export type ComplaintStatus = 'open' | 'in_progress' | 'resolved' | 'closed';

export interface Complaint {
  id: number;
  gym_id: number;
  branch_id: number | null;
  member_id: number | null;
  category: string;
  description: string;
  status: ComplaintStatus;
  assigned_to: number | null;
  resolution_notes: string | null;
  created_at: string;
  updated_at: string;
}

export interface CreateComplaintPayload {
  category: string;
  description: string;
  member_id?: number | null;
  assigned_to?: number | null;
}

export type EquipmentStatus = 'operational' | 'under_maintenance' | 'retired';

export interface Equipment {
  id: number;
  gym_id: number;
  branch_id: number | null;
  name: string;
  category: string;
  serial_number: string | null;
  purchased_on: string | null;
  status: EquipmentStatus;
  notes: string | null;
}

export interface CreateEquipmentPayload {
  name: string;
  category: string;
  serial_number?: string | null;
  purchased_on?: string | null;
  notes?: string | null;
}

export type MaintenanceStatus = 'scheduled' | 'done' | 'skipped';

export interface MaintenanceSchedule {
  id: number;
  gym_id: number;
  branch_id: number | null;
  equipment_id: number;
  title: string;
  due_on: string;
  interval_days: number | null;
  status: MaintenanceStatus;
  completed_on: string | null;
  notes: string | null;
}

export interface CreateMaintenancePayload {
  title: string;
  due_on: string;
  interval_days?: number | null;
  notes?: string | null;
}

export interface Trainer {
  id: number;
  gym_id: number;
  branch_id: number | null;
  user_id: number | null;
  full_name: string;
  phone: string;
  specialty: string | null;
  bio: string | null;
  is_active: boolean;
}

export interface CreateTrainerPayload {
  full_name: string;
  phone: string;
  specialty?: string | null;
  bio?: string | null;
  user_id?: number | null;
  is_active?: boolean;
}

export interface TrainerAvailability {
  id: number;
  trainer_id: number;
  weekday: number;
  start_time: string;
  end_time: string;
}

export interface TrainerAssignment {
  id: number;
  trainer_id: number;
  member_id: number;
  is_active: boolean;
}

export type SessionStatus = 'scheduled' | 'completed' | 'cancelled' | 'no_show';

export interface TrainingSession {
  id: number;
  gym_id: number;
  branch_id: number | null;
  trainer_id: number;
  member_id: number;
  start_at: string;
  end_at: string;
  status: SessionStatus;
  notes: string | null;
}

export interface CreateSessionPayload {
  trainer_id: number;
  member_id: number;
  start_at: string;
  end_at: string;
  notes?: string | null;
}

export interface TrainerAttendance {
  id: number;
  trainer_id: number;
  session_id: number;
  checked_in_at: string;
  checked_out_at: string | null;
  notes: string | null;
}

export type StaffAttendanceStatus = 'present' | 'absent' | 'half_day' | 'leave';

export interface StaffAttendance {
  id: number;
  gym_id: number;
  branch_id: number | null;
  user_id: number;
  on_date: string;
  status: StaffAttendanceStatus;
  check_in: string | null;
  check_out: string | null;
  notes: string | null;
}

export interface PayrollRecord {
  id: number;
  gym_id: number;
  branch_id: number | null;
  user_id: number;
  month: string;
  base_paise: number;
  bonus_paise: number;
  deductions_paise: number;
  net_paise: number;
  status: string;
  notes: string | null;
}

export interface Expense {
  id: number;
  gym_id: number;
  branch_id: number | null;
  category: string;
  amount_paise: number;
  spent_on: string;
  vendor: string | null;
  notes: string | null;
}

export interface CreateExpensePayload {
  category: string;
  amount_paise: number;
  spent_on: string;
  vendor?: string | null;
  notes?: string | null;
}

export interface FinancePeriodSummary {
  from_date: string;
  to_date: string;
  revenue_paise: number;
  expense_paise: number;
  profit_paise: number;
  payments_count: number;
}

export interface DailyDashboard {
  on_date: string;
  revenue_paise: number;
  expense_paise: number;
  profit_paise: number;
  payments_count: number;
}
