import { Component, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { SalesService } from '../../services/sales.service';
import { BillingService } from '../../../billing/services/billing.service';
import { Sale, PaymentMethod } from '../../models/sale.model';
import { Invoice } from '../../../billing/models/invoice.model';
import { INVOICE_STATUS_LABELS, INVOICE_STATUS_TONES } from '../../../billing/models/invoice-status.const';
import { ToastService } from '../../../../core/services/toast.service';
import { PageHeader } from '../../../../shared/components/page-header/page-header';
import { Button } from '../../../../shared/components/button/button';
import { DataTable, DataTableColumn } from '../../../../shared/components/data-table/data-table';
import { Modal } from '../../../../shared/components/modal/modal';
import { StatusBadge } from '../../../../shared/components/status-badge/status-badge';
import { Icon } from '../../../../shared/components/icon/icon';

const PAYMENT_LABELS: Record<PaymentMethod, string> = {
  efectivo: 'Efectivo',
  tarjeta: 'Tarjeta',
  transferencia: 'Transferencia',
};

type InvoiceFilter = 'all' | 'authorized' | 'pending' | 'rejected' | 'none';

const FILTERS: { value: InvoiceFilter; label: string }[] = [
  { value: 'all', label: 'Todas' },
  { value: 'authorized', label: 'Autorizadas' },
  { value: 'pending', label: 'En proceso' },
  { value: 'rejected', label: 'Rechazadas' },
  { value: 'none', label: 'Sin factura' },
];

const ID_PATTERN = /^\d{10}(\d{3})?$/;
const FINAL_CONSUMER_ID = '9999999999';

/** Fecha corta y consistente en toda la pantalla: 02/09/2026 09:00. */
function formatDateTime(iso: string): string {
  return new Date(iso).toLocaleString('es-EC', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
  });
}

/** Una venta junto con su factura electrónica (si la tiene). */
export interface SaleRow extends Sale {
  invoice: Invoice | undefined;
}

function matchesFilter(row: SaleRow, filter: InvoiceFilter): boolean {
  const status = row.invoice?.status;
  switch (filter) {
    case 'authorized':
      return status === 'autorizada';
    case 'pending':
      return status === 'pendiente' || status === 'procesando' || status === 'borrador';
    case 'rejected':
      return status === 'rechazada';
    case 'none':
      return !row.invoice;
    default:
      return true;
  }
}

@Component({
  selector: 'app-sales-history',
  imports: [RouterLink, FormsModule, PageHeader, Button, DataTable, Modal, StatusBadge, Icon],
  templateUrl: './sales-history.html',
  styleUrl: './sales-history.scss',
})
export class SalesHistory {
  private salesService = inject(SalesService);
  private billingService = inject(BillingService);
  private toast = inject(ToastService);

  readonly filters = FILTERS;
  readonly paymentLabels = PAYMENT_LABELS;
  readonly statusLabels = INVOICE_STATUS_LABELS;
  readonly statusTones = INVOICE_STATUS_TONES;
  readonly trackById = (row: SaleRow): string => row.id;

  filter = signal<InvoiceFilter>('all');
  selectedId = signal<string | null>(null);
  busy = signal(false);

  // Datos de facturación editables en el detalle (para emitir o corregir y reintentar).
  idDraft = signal(FINAL_CONSUMER_ID);
  emailDraft = signal('');

  rows = computed<SaleRow[]>(() => {
    const invoiceBySale = new Map<string, Invoice>();
    for (const invoice of this.billingService.invoices()) {
      if (invoice.saleId) invoiceBySale.set(invoice.saleId, invoice);
    }
    return this.salesService.sales().map((sale) => ({ ...sale, invoice: invoiceBySale.get(sale.id) }));
  });

  visibleRows = computed(() => this.rows().filter((row) => matchesFilter(row, this.filter())));

  counts = computed(() => {
    const rows = this.rows();
    return Object.fromEntries(FILTERS.map((f) => [f.value, rows.filter((row) => matchesFilter(row, f.value)).length]));
  });

  /** La venta abierta en el detalle; se recalcula sola cuando cambia el estado de su factura. */
  selected = computed(() => this.rows().find((row) => row.id === this.selectedId()) ?? null);

  idError = computed(() => (ID_PATTERN.test(this.idDraft().trim()) ? '' : 'Ingresa una cédula (10 dígitos) o un RUC (13 dígitos).'));

  columns: DataTableColumn<SaleRow>[] = [
    { key: 'folio', header: 'N°', cell: (s) => s.folio, sortable: true },
    { key: 'date', header: 'Fecha', cell: (s) => formatDateTime(s.date), sortable: true },
    { key: 'customerName', header: 'Cliente', cell: (s) => s.customerName, sortable: true },
    { key: 'total', header: 'Total', cell: (s) => `$${s.total.toFixed(2)}`, align: 'right' },
    { key: 'paymentMethod', header: 'Pago', cell: (s) => PAYMENT_LABELS[s.paymentMethod] },
    {
      key: 'invoice',
      header: 'Factura',
      cell: (s) => (s.invoice ? INVOICE_STATUS_LABELS[s.invoice.status] : 'Sin factura'),
      badge: (s) =>
        s.invoice
          ? { label: INVOICE_STATUS_LABELS[s.invoice.status], tone: INVOICE_STATUS_TONES[s.invoice.status] }
          : { label: 'Sin factura', tone: 'neutral' },
    },
    { key: 'createdBy', header: 'Usuario', cell: (s) => s.createdBy },
  ];

  open(row: SaleRow): void {
    this.selectedId.set(row.id);
    this.idDraft.set(row.invoice?.customer.rucOrCedula ?? FINAL_CONSUMER_ID);
    this.emailDraft.set(row.invoice?.customer.email ?? '');
  }

  close(): void {
    this.selectedId.set(null);
  }

  issueInvoice(row: SaleRow): void {
    if (this.idError() || this.busy()) return;
    this.busy.set(true);
    this.billingService.invoiceSale(row, this.#customerFor(row)).subscribe({
      next: (invoice) => this.#finish(invoice),
      error: () => this.#fail(),
    });
  }

  retryInvoice(row: SaleRow): void {
    if (!row.invoice || this.idError() || this.busy()) return;
    this.busy.set(true);
    this.billingService.retry(row.invoice.id, this.#customerFor(row)).subscribe({
      next: (invoice) => this.#finish(invoice),
      error: () => this.#fail(),
    });
  }

  #customerFor(row: SaleRow): Invoice['customer'] {
    return { rucOrCedula: this.idDraft().trim(), razonSocial: row.customerName, email: this.emailDraft().trim() };
  }

  #finish(invoice: Invoice): void {
    this.busy.set(false);
    if (invoice.status === 'autorizada') this.toast.success(`Factura ${invoice.numero} autorizada.`);
    else this.toast.error(`Factura ${invoice.numero} rechazada.`);
  }

  #fail(): void {
    this.busy.set(false);
    this.toast.error('No se pudo emitir la factura. Inténtalo de nuevo.');
  }

  formatDate(iso: string): string {
    return formatDateTime(iso);
  }
}
