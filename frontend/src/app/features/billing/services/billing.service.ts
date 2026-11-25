import { Injectable, inject, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, map, tap } from 'rxjs';

import { environment } from '../../../../environments/environment';
import { Invoice } from '../models/invoice.model';
import { InvoiceDto, invoiceFromDto } from '../models/invoice.mapper';
import { Sale } from '../../sales/models/sale.model';

/**
 * Facturas electrónicas emitidas por el backend (`POST /api/sales/{id}/invoice`).
 *
 * El estado de cada factura llega dentro de la venta (`Sale.invoice`). `invoices` guarda solo
 * las emitidas en esta sesión, para mostrarlas al instante sin volver a pedir el historial.
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
   * Si la factura anterior fue rechazada por el SRI, el backend la vuelve a emitir.
   */
  invoiceSale(sale: Sale, email = ''): Observable<Invoice> {
    return this.http.post<InvoiceDto>(`${this.salesUrl}/${encodeURIComponent(sale.id)}/invoice`, {}).pipe(
      map((dto) => invoiceFromDto(dto, sale, email)),
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
}
