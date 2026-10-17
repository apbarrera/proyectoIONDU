import { BadgeTone } from '../../../shared/components/status-badge/status-badge';
import { InvoiceStatus } from './invoice.model';

export const INVOICE_STATUS_LABELS: Record<InvoiceStatus, string> = {
  borrador: 'Borrador',
  procesando: 'Procesando',
  pendiente: 'Pendiente',
  autorizada: 'Autorizada',
  rechazada: 'Rechazada',
};

export const INVOICE_STATUS_TONES: Record<InvoiceStatus, BadgeTone> = {
  borrador: 'neutral',
  procesando: 'info',
  pendiente: 'warning',
  autorizada: 'success',
  rechazada: 'danger',
};
