import { Injectable, inject, signal } from '@angular/core';
import { Observable, map, switchMap, tap } from 'rxjs';
import { Invoice, InvoiceCustomer, InvoiceStatus } from '../models/invoice.model';
import { Sale, SaleLineItem } from '../../sales/models/sale.model';
import { INVOICES_MOCK } from '../../../mocks/billing.mock';
import { simulateRequest } from '../../../core/services/mock-http.util';
import { generateId } from '../../../core/utils/id.util';
import { BillingAdapterService } from './billing-adapter.service';
import { AuditService } from '../../../core/services/audit.service';
import { AuthService } from '../../../core/services/auth.service';
import { TenantService } from '../../../core/services/tenant.service';

export interface NewInvoiceInput {
  saleId?: string;
  customer: InvoiceCustomer;
  items: SaleLineItem[];
}

@Injectable({ providedIn: 'root' })
export class BillingService {
  private adapter = inject(BillingAdapterService);
  private audit = inject(AuditService);
  private auth = inject(AuthService);
  private tenant = inject(TenantService);

  #invoices = signal<Invoice[]>(INVOICES_MOCK);
  readonly invoices = this.#invoices.asReadonly();

  getInvoices(): Observable<Invoice[]> {
    return simulateRequest(this.#invoices());
  }

  getInvoice(id: string): Invoice | undefined {
    return this.#invoices().find((i) => i.id === id);
  }

  createDraft(input: NewInvoiceInput): Observable<Invoice> {
    const ivaRate = this.tenant.tenant().ivaRate;
    const subtotal = Math.round(input.items.reduce((sum, i) => sum + i.subtotal, 0) * 100) / 100;
    const iva = Math.round(subtotal * ivaRate * 100) / 100;
    const now = new Date().toISOString();

    const invoice: Invoice = {
      id: generateId(),
      saleId: input.saleId,
      numero: this.#nextNumero(),
      claveAcceso: null,
      customer: input.customer,
      items: input.items,
      subtotal,
      iva,
      total: Math.round((subtotal + iva) * 100) / 100,
      status: 'borrador',
      statusHistory: [{ status: 'borrador', timestamp: now }],
      createdAt: now,
      createdBy: this.auth.currentUser()?.fullName ?? 'Usuario',
    };

    this.#invoices.update((list) => [invoice, ...list]);
    return simulateRequest(invoice);
  }

  /** Factura vinculada a una venta, si la tiene. */
  getInvoiceForSale(saleId: string): Invoice | undefined {
    return this.#invoices().find((i) => i.saleId === saleId);
  }

  /** Crea la factura de una venta y la envía a autorización. Se usa al vender y al emitir después. */
  invoiceSale(sale: Sale, customer: InvoiceCustomer): Observable<Invoice> {
    return this.createDraft({ saleId: sale.id, customer, items: sale.items }).pipe(
      switchMap((draft) => this.emit(draft.id)),
    );
  }

  /** Reintenta una factura rechazada, opcionalmente corrigiendo antes los datos del cliente. */
  retry(invoiceId: string, customer?: InvoiceCustomer): Observable<Invoice> {
    if (customer) {
      this.#invoices.update((list) => list.map((inv) => (inv.id === invoiceId ? { ...inv, customer } : inv)));
    }
    return this.emit(invoiceId);
  }

  /** Walks a draft invoice through borrador → procesando → pendiente → autorizada/rechazada. */
  emit(invoiceId: string): Observable<Invoice> {
    this.#transition(invoiceId, 'procesando');

    return simulateRequest(null, { minDelay: 900, maxDelay: 1300 }).pipe(
      tap(() => this.#transition(invoiceId, 'pendiente')),
      switchMap(() => this.adapter.submit(invoiceId)),
      tap((result) => this.#finalize(invoiceId, result.status, result.claveAcceso, result.rejectionReason)),
      map(() => this.getInvoice(invoiceId)!),
    );
  }

  #transition(invoiceId: string, status: InvoiceStatus): void {
    this.#invoices.update((list) =>
      list.map((inv) =>
        inv.id === invoiceId
          ? { ...inv, status, statusHistory: [...inv.statusHistory, { status, timestamp: new Date().toISOString() }] }
          : inv,
      ),
    );
  }

  #finalize(invoiceId: string, status: InvoiceStatus, claveAcceso: string, rejectionReason?: string): void {
    const now = new Date().toISOString();
    this.#invoices.update((list) =>
      list.map((inv) =>
        inv.id === invoiceId
          ? {
              ...inv,
              status,
              claveAcceso,
              rejectionReason,
              authorizedAt: status === 'autorizada' ? now : inv.authorizedAt,
              statusHistory: [...inv.statusHistory, { status, timestamp: now }],
            }
          : inv,
      ),
    );

    const invoice = this.getInvoice(invoiceId);
    const user = this.auth.currentUser();
    this.audit.log({
      userId: user?.id ?? '',
      userName: user?.fullName ?? 'Usuario',
      module: 'facturacion',
      action: status === 'autorizada' ? 'Factura autorizada' : 'Factura rechazada',
      description: `Factura ${invoice?.numero} fue ${status === 'autorizada' ? 'autorizada' : 'rechazada'} por el servicio de facturación.`,
    });
  }

  #nextNumero(): string {
    const seq = this.#invoices().length + 99;
    return `001-001-${String(seq).padStart(9, '0')}`;
  }
}
