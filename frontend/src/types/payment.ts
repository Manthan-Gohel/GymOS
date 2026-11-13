export interface Invoice {
  id: number;
  gym_id: number;
  branch_id?: number | null;
  invoice_number: string;
  member_id: number;
  membership_id?: number | null;
  taxable_value_paise: number;
  gst_rate: number;
  cgst_paise: number;
  sgst_paise: number;
  igst_paise: number;
  total_paise: number;
  late_fee_paise: number;
  status: 'issued' | 'partial' | 'paid' | 'cancelled';
  created_at?: string;
}

export interface Payment {
  id: number;
  gym_id: number;
  branch_id?: number | null;
  invoice_id?: number | null;
  membership_id?: number | null;
  member_id: number;
  amount_paise: number;
  method: 'cash' | 'upi' | 'card' | 'mock';
  reference?: string | null;
  status: 'paid' | 'pending' | 'failed';
  recorded_by: number;
  created_at?: string;
}

export interface MemberDues {
  member_id: number;
  total_invoiced_paise: number;
  total_paid_paise: number;
  dues_paise: number;
}

export interface RecordPaymentPayload {
  member_id: number;
  amount_paise: number;
  method: 'cash' | 'upi' | 'card' | 'mock';
  invoice_id?: number;
  membership_id?: number;
  reference?: string;
}
