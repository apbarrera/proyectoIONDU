import { Injectable, inject, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, map, tap } from 'rxjs';

import { environment } from '../../../../environments/environment';
import { Invoice, InvoiceStatus } from '../models/invoice.model';
import { Sale } from '../../sales/models/sale.model';

type BackendInvoiceStatus = 'autorizada' | 'rechazada' | 'por_enviar' | 'por_autorizar';

interface InvoiceDto {
  id: number;
  saleId: number;
  invoiceNumber: string;
  accessKey: string;
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

/**
 * Facturas electrónicas emitidas por el backend (`POST /api/sales/{id}/invoice`).
 *
 * Todavía no existe un endpoint para listar facturas ni la venta trae su estado, así que
 * `invoices` solo contiene las emitidas en esta sesión del navegador.
 */
@Injectable({ providedIn: 'root' })
export class BillingService {
  private readonly http = inject(HttpClient);
  private readonly salesUrl = `${environment.apiUrl}/sales`;

  #invoices = signal<Invoice[]>([]);
  readonly invoices = this.#invoices.asReadonly();

  getInvoiceForSale(saleId: string): Invoice | undefined {
    return this.#invoices().find((i) => i.saleId === saleId);
  }

  /**
   * Emite la factura electrónica de una venta: el backend arma el XML, lo firma con el `.p12`
   * de la empresa, lo envía al SRI y genera el RIDE. El cliente sale de la propia venta.
   */
  invoiceSale(sale: Sale, email = ''): Observable<Invoice> {
    return this.http.post<InvoiceDto>(`${this.salesUrl}/${encodeURIComponent(sale.id)}/invoice`, {}).pipe(
      map((dto) => this.toInvoice(dto, sale, email)),
      tap((invoice) =>
        this.#invoices.update((list) => [invoice, ...list.filter((i) => i.saleId !== invoice.saleId)]),
      ),
    );
  }

  /** Descarga el RIDE (PDF) de la factura de una venta. */
  downloadRide(saleId: string): Observable<Blob> {
    return this.http.get(`${this.salesUrl}/${encodeURIComponent(saleId)}/invoice/ride`, {
      responseType: 'blob',
    });
  }

  private toInvoice(dto: InvoiceDto, sale: Sale, email: string): Invoice {
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
      rejectionReason: status === 'rechazada' ? (errors.join(' ') || 'El SRI rechazó la factura.') : undefined,
      createdAt: dto.issueDate,
      authorizedAt: dto.authorizationDate ?? undefined,
    };
  }
}
