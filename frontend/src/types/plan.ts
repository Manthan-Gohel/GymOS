export interface MembershipPlan {
  id: number;
  gym_id: number;
  branch_id: number | null;
  name: string;
  duration_days: number;
  price_paise: number;
  currency: string;
  terms: string | null;
  is_active: boolean;
}

export interface CreatePlanPayload {
  name: string;
  duration_days: number;
  price_paise: number;
  currency?: string;
  terms?: string | null;
  is_active?: boolean;
}

export type MembershipStatus = 'active' | 'frozen' | 'expired' | 'upgraded';

export interface Membership {
  id: number;
  gym_id: number;
  branch_id: number | null;
  member_id: number;
  plan_id: number;
  status: MembershipStatus;
  start_date: string;
  end_date: string;
  frozen_on: string | null;
  upgraded_to_id: number | null;
}

export interface PurchaseMembershipPayload {
  member_id: number;
  plan_id: number;
  start_date: string;
}
