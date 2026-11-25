export type ExpensePaymentMethod =
  | 'efectivo'
  | 'tarjeta_debito'
  | 'tarjeta_credito'
  | 'transferencia'
  | 'cheque';
export type ExpenseSourceType = 'manual' | 'email';

export interface ExpenseCategory {
  id: number;
  name: string;
  description: string | null;
  predefined: boolean;
}

export interface Supplier {
  id: number;
  identification: string;
  name: string;
  phone: string | null;
  email: string | null;
  address: string | null;
  identificationWarning: string | null;
}

/** Gasto tal como lo guarda el backend: solo tiene el total (la base no separa el IVA todavía). */
export interface Expense {
  id: string;
  date: string;
  categoryId: number;
  category: string;
  supplierId: number | null;
  /** Vacío si el gasto no tiene proveedor. */
  providerName: string;
  providerRuc: string;
  total: number;
  paymentMethod: ExpensePaymentMethod;
  description: string;
  receiptNumber?: string;
  sourceType: ExpenseSourceType;
}
