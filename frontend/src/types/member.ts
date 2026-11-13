export interface Member {
  id: number;
  gym_id: number;
  branch_id?: number | null;
  full_name: string;
  phone: string;
  email?: string | null;
  profile_photo_ref?: string | null;
  kyc_id_type?: string | null;
  kyc_id_number?: string | null;
  emergency_contact_name?: string | null;
  emergency_contact_phone?: string | null;
  health_notes?: string | null;
  whatsapp_consent: boolean;
  opted_out: boolean;
  is_active: boolean;
  created_at?: string;
  updated_at?: string;
}

export interface CreateMemberPayload {
  full_name: string;
  phone: string;
  email?: string;
  profile_photo_ref?: string;
  kyc_id_type?: string;
  kyc_id_number?: string;
  emergency_contact_name?: string;
  emergency_contact_phone?: string;
  health_notes?: string;
  whatsapp_consent?: boolean;
}
