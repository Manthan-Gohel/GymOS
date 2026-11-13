export type UserRole = 'owner' | 'admin' | 'reception' | 'trainer';

export interface User {
  id: number;
  email: string;
  gym_id: number;
  branch_id?: number | null;
  full_name?: string;
  roles: UserRole[];
}

export interface LoginRequest {
  gym_id: number;
  email: string;
  password: string;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
}

export interface TokenClaims {
  sub: string;
  gym_id: number;
  roles: UserRole[];
  exp?: number;
}
