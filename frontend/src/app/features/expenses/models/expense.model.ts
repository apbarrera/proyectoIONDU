export type ExpensePaymentMethod = 'efectivo' | 'tarjeta' | 'transferencia' | 'cheque';
export type ExpenseSourceType = 'manual' | 'email';

export interface Expense {
  id: string;
  date: string;
  category: string;
  providerName: string;
  providerRuc: string;
  amount: number;
  ivaAmount: number;
  total: number;
  paymentMethod: ExpensePaymentMethod;
  description: string;
  observation?: string;
  sourceType: ExpenseSourceType;
  createdBy: string;
}
