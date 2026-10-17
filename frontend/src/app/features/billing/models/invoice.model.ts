import { SaleLineItem } from '../../sales/models/sale.model';

export type InvoiceStatus = 'borrador' | 'procesando' | 'pendiente' | 'autorizada' | 'rechazada';

export interface InvoiceStatusEvent {
  status: InvoiceStatus;
  timestamp: string;
}

export interface InvoiceCustomer {
  rucOrCedula: string;
  razonSocial: string;
  email: string;
}

export interface Invoice {
  id: string;
  saleId?: string;
  numero: string;
  claveAcceso: string | null;
  customer: InvoiceCustomer;
  items: SaleLineItem[];
  subtotal: number;
  iva: number;
  total: number;
  status: InvoiceStatus;
  statusHistory: InvoiceStatusEvent[];
  rejectionReason?: string;
  createdAt: string;
  authorizedAt?: string;
  createdBy: string;
}
