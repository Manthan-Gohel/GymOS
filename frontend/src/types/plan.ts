export interface MembershipPlan {
  id: number;
  gym_id: number;
  branch_id?: number | null;
  name: string;
  duration_days: number;
  price_paise: number;
  currency: string;
  terms_json?: Record<string, unknown> | null;
  is_active: boolean;
  created_at?: string;
  updated_at?: string;
}

export interface CreatePlanPayload {
  name: string;
  duration_days: number;
  price_paise: number;
  currency?: string;
  terms_json?: Record<string, unknown>;
  is_active?: boolean;
}

export interface Membership {
  id: number;
  gym_id: number;
  branch_id?: number | null;
  member_id: number;
  plan_id: number;
  start_date: string;
  end_date: string;
  status: 'active' | 'frozen' | 'expired' | 'upgraded';
  frozen_days: number;
  created_at?: string;
}

export interface PurchaseMembershipPayload {
  member_id: number;
  plan_id: number;
  start_date?: string;
}
