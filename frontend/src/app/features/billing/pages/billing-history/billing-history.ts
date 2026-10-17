import { Component, inject, signal } from '@angular/core';
import { DatePipe } from '@angular/common';
import { RouterLink } from '@angular/router';
import { BillingService } from '../../services/billing.service';
import { Invoice, InvoiceStatus } from '../../models/invoice.model';
import { PageHeader } from '../../../../shared/components/page-header/page-header';
import { Button } from '../../../../shared/components/button/button';
import { DataTable, DataTableColumn } from '../../../../shared/components/data-table/data-table';
import { StatusBadge, BadgeTone } from '../../../../shared/components/status-badge/status-badge';
import { Modal } from '../../../../shared/components/modal/modal';
import { Icon } from '../../../../shared/components/icon/icon';

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

@Component({
  selector: 'app-billing-history',
  imports: [RouterLink, DatePipe, PageHeader, Button, DataTable, StatusBadge, Modal, Icon],
  templateUrl: './billing-history.html',
  styleUrl: './billing-history.scss',
})
export class BillingHistory {
  billingService = inject(BillingService);
  statusLabels = INVOICE_STATUS_LABELS;
  statusTones = INVOICE_STATUS_TONES;

  selected = signal<Invoice | null>(null);

  columns: DataTableColumn<Invoice>[] = [
    { key: 'numero', header: 'N° Factura', cell: (i) => i.numero, sortable: true },
    { key: 'createdAt', header: 'Fecha', cell: (i) => new Date(i.createdAt).toLocaleString('es-EC'), sortable: true },
    { key: 'razonSocial', header: 'Cliente', cell: (i) => i.customer.razonSocial, sortable: true },
    { key: 'total', header: 'Total', cell: (i) => `$${i.total.toFixed(2)}`, align: 'right' },
    { key: 'status', header: 'Estado', cell: (i) => INVOICE_STATUS_LABELS[i.status] },
  ];

  openDetail(invoice: Invoice): void {
    this.selected.set(invoice);
  }

  closeDetail(): void {
    this.selected.set(null);
  }
}
