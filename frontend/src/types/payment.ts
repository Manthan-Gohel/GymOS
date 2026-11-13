export type InvoiceStatus = 'issued' | 'partial' | 'paid' | 'cancelled';

export interface Invoice {
  id: number;
  gym_id: number;
  branch_id: number | null;
  member_id: number;
  membership_id: number | null;
  payment_id: number | null;
  invoice_number: string;
  status: InvoiceStatus;
  taxable_value_paise: number;
  gst_rate: number;
  cgst_paise: number;
  sgst_paise: number;
  igst_paise: number;
  late_fee_paise: number;
  total_paise: number;
  currency: string;
  seller_gstin: string | null;
  buyer_name: string | null;
  buyer_gstin: string | null;
  notes: string | null;
  meta: Record<string, unknown> | null;
}

export type PaymentMethod = 'cash' | 'upi' | 'card' | 'mock';
export type PaymentStatus = 'paid' | 'pending' | 'failed' | 'refunded';

export interface Payment {
  id: number;
  gym_id: number;
  branch_id: number | null;
  member_id: number;
  membership_id: number | null;
  invoice_id: number | null;
  amount_paise: number;
  method: PaymentMethod;
  status: PaymentStatus;
  reference: string | null;
  notes: string | null;
  paid_at: string;
  recorded_by: number;
}

export interface InvoiceDue {
  invoice_id: number;
  invoice_number: string;
  status: InvoiceStatus;
  due_paise: number;
}

export interface MemberDues {
  member_id: number;
  total_due_paise: number;
  invoices: InvoiceDue[];
}

export interface RecordPaymentPayload {
  member_id: number;
  amount_paise: number;
  method: PaymentMethod;
  invoice_id?: number;
  membership_id?: number;
  reference?: string;
  notes?: string;
  paid_at?: string;
}

/** Response of POST /payments and POST /payments/{id}/status. */
export interface PaymentResult {
  payment: Payment;
  invoice: Invoice | null;
  dues: MemberDues;
}
