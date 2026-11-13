import {
  LoginRequest,
  LoginResponse,
  User,
} from '../types/auth';
import {
  Member,
  CreateMemberPayload,
} from '../types/member';
import {
  MembershipPlan,
  CreatePlanPayload,
  Membership,
  PurchaseMembershipPayload,
} from '../types/plan';
import {
  Invoice,
  Payment,
  MemberDues,
  RecordPaymentPayload,
} from '../types/payment';

const BASE_URL = '';

class ApiService {
  private getToken(): string | null {
    return localStorage.getItem('gymos_token');
  }

  private async request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
    const token = this.getToken();
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      ...(options.headers as Record<string, string>),
    };

    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    const response = await fetch(`${BASE_URL}${endpoint}`, {
      ...options,
      headers,
    });

    if (!response.ok) {
      let errorMessage = 'Request failed';
      try {
        const errorData = await response.json();
        errorMessage = errorData.detail || errorData.message || errorMessage;
      } catch {
        errorMessage = response.statusText;
      }
      throw new Error(errorMessage);
    }

    return response.json() as Promise<T>;
  }

  // Auth endpoints
  async login(payload: LoginRequest): Promise<LoginResponse> {
    return this.request<LoginResponse>('/auth/login', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  }

  async getMe(): Promise<User> {
    return this.request<User>('/auth/me');
  }

  // Members endpoints
  async getMembers(): Promise<Member[]> {
    return this.request<Member[]>('/members');
  }

  async getMember(id: number): Promise<Member> {
    return this.request<Member>(`/members/${id}`);
  }

  async createMember(payload: CreateMemberPayload): Promise<Member> {
    return this.request<Member>('/members', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  }

  async updateMember(id: number, payload: Partial<Member>): Promise<Member> {
    return this.request<Member>(`/members/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(payload),
    });
  }

  // Plans endpoints
  async getPlans(): Promise<MembershipPlan[]> {
    return this.request<MembershipPlan[]>('/plans');
  }

  async createPlan(payload: CreatePlanPayload): Promise<MembershipPlan> {
    return this.request<MembershipPlan>('/plans', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  }

  async updatePlan(id: number, payload: Partial<MembershipPlan>): Promise<MembershipPlan> {
    return this.request<MembershipPlan>(`/plans/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(payload),
    });
  }

  // Membership lifecycle endpoints
  async getMemberships(memberId?: number): Promise<Membership[]> {
    const url = memberId ? `/memberships?member_id=${memberId}` : '/memberships';
    return this.request<Membership[]>(url);
  }

  async purchaseMembership(payload: PurchaseMembershipPayload): Promise<Membership> {
    return this.request<Membership>('/memberships/purchase', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  }

  async freezeMembership(id: number, days: number): Promise<Membership> {
    return this.request<Membership>(`/memberships/${id}/freeze`, {
      method: 'POST',
      body: JSON.stringify({ days }),
    });
  }

  async unfreezeMembership(id: number): Promise<Membership> {
    return this.request<Membership>(`/memberships/${id}/unfreeze`, {
      method: 'POST',
    });
  }

  async upgradeMembership(id: number, newPlanId: number): Promise<Membership> {
    return this.request<Membership>(`/memberships/${id}/upgrade`, {
      method: 'POST',
      body: JSON.stringify({ new_plan_id: newPlanId }),
    });
  }

  // Invoices & Payments endpoints
  async getInvoices(): Promise<Invoice[]> {
    return this.request<Invoice[]>('/invoices');
  }

  async recordPayment(payload: RecordPaymentPayload): Promise<Payment> {
    return this.request<Payment>('/payments', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  }

  async getMemberDues(memberId: number): Promise<MemberDues> {
    return this.request<MemberDues>(`/payments/dues?member_id=${memberId}`);
  }
}

export const api = new ApiService();
