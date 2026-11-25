import { Sale } from '../../sales/models/sale.model';
import { Invoice, InvoiceStatus } from './invoice.model';

export type BackendInvoiceStatus = 'autorizada' | 'rechazada' | 'por_enviar' | 'por_autorizar';

/** Factura tal como la devuelve el backend (`Invoice` en API.md). */
export interface InvoiceDto {
  id: number;
  saleId: number;
  invoiceNumber: string;
  accessKey: string | null;
  authorizationStatus: BackendInvoiceStatus;
  authorizationNumber: string | null;
  authorizationDate: string | null;
  messages: { identifier: string; message: string; additionalInformation: string | null; type: string }[];
  issueDate: string;
  subtotal: number;
  taxes: number;
  total: number;
}

const STATUS_MAP: Record<BackendInvoiceStatus, InvoiceStatus> = {
  autorizada: 'autorizada',
  rechazada: 'rechazada',
  por_enviar: 'procesando',
  por_autorizar: 'pendiente',
};

/** Convierte la factura del backend al modelo del frontend; el cliente y las líneas salen de la venta. */
export function invoiceFromDto(
  dto: InvoiceDto,
  sale: Pick<Sale, 'customerIdentification' | 'customerName' | 'items'>,
  email = '',
): Invoice {
  const status = STATUS_MAP[dto.authorizationStatus];
  const errors = dto.messages.filter((m) => m.type === 'ERROR').map((m) => m.message);

  return {
    id: String(dto.id),
    saleId: String(dto.saleId),
    numero: dto.invoiceNumber,
    claveAcceso: dto.accessKey,
    customer: {
      rucOrCedula: sale.customerIdentification ?? '9999999999999',
      razonSocial: sale.customerName,
      email,
    },
    items: sale.items,
    subtotal: dto.subtotal,
    iva: dto.taxes,
    total: dto.total,
    status,
    statusHistory: [{ status, timestamp: dto.authorizationDate ?? dto.issueDate }],
    rejectionReason: status === 'rechazada' ? errors.join(' ') || 'El SRI rechazó la factura.' : undefined,
    createdAt: dto.issueDate,
    authorizedAt: dto.authorizationDate ?? undefined,
  };
}
