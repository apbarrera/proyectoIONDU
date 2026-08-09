export type PaymentMethod = 'efectivo' | 'tarjeta' | 'transferencia';
export type SaleStatus = 'completada' | 'anulada';

export interface SaleLineItem {
  productId: string;
  productName: string;
  quantity: number;
  unitPrice: number;
  subtotal: number;
}

export interface Sale {
  id: string;
  folio: string;
  date: string;
  customerName: string;
  items: SaleLineItem[];
  subtotal: number;
  ivaAmount: number;
  total: number;
  paymentMethod: PaymentMethod;
  status: SaleStatus;
  observation?: string;
  createdBy: string;
}
