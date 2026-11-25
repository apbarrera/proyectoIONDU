import type { Invoice } from '../../billing/models/invoice.model';

export type PaymentMethod = 'efectivo' | 'tarjeta_debito' | 'tarjeta_credito' | 'transferencia';
export type SaleStatus = 'completada' | 'anulada';

export interface SaleLineItem {
  /** Vacío en las líneas de concepto libre (sin producto). */
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
  /** `null` = consumidor final. */
  customerId?: number | null;
  customerName: string;
  customerIdentification?: string | null;
  items: SaleLineItem[];
  subtotal: number;
  ivaAmount: number;
  total: number;
  paymentMethod: PaymentMethod;
  status: SaleStatus;
  observation?: string;
  /** Nombre de quien registró la venta en la empresa. */
  createdBy?: string;
  /** Factura electrónica de la venta; `undefined` si todavía no se factura. */
  invoice?: Invoice;
}
