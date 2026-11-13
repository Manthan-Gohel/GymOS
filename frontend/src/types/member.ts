export interface Member {
  id: number;
  gym_id: number;
  branch_id: number | null;
  full_name: string;
  phone: string;
  email: string | null;
  photo_ref: string | null;
  kyc_id_type: string | null;
  kyc_id_number: string | null;
  address: string | null;
  emergency_contact_name: string | null;
  emergency_contact_phone: string | null;
  health_notes: string | null;
  whatsapp_consent: boolean;
  whatsapp_opt_out: boolean;
  is_active: boolean;
}

export interface CreateMemberPayload {
  full_name: string;
  phone: string;
  email?: string | null;
  photo_ref?: string | null;
  kyc_id_type?: string | null;
  kyc_id_number?: string | null;
  address?: string | null;
  emergency_contact_name?: string | null;
  emergency_contact_phone?: string | null;
  health_notes?: string | null;
  whatsapp_consent?: boolean;
}

export type UpdateMemberPayload = Partial<CreateMemberPayload> & {
  whatsapp_opt_out?: boolean;
  is_active?: boolean;
};
