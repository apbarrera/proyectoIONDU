import { Component, inject } from '@angular/core';
import { RouterLink } from '@angular/router';
import { SalesService } from '../../services/sales.service';
import { Sale, PaymentMethod } from '../../models/sale.model';
import { PageHeader } from '../../../../shared/components/page-header/page-header';
import { Button } from '../../../../shared/components/button/button';
import { DataTable, DataTableColumn } from '../../../../shared/components/data-table/data-table';

const PAYMENT_LABELS: Record<PaymentMethod, string> = {
  efectivo: 'Efectivo',
  tarjeta: 'Tarjeta',
  transferencia: 'Transferencia',
};

@Component({
  selector: 'app-sales-history',
  imports: [RouterLink, PageHeader, Button, DataTable],
  templateUrl: './sales-history.html',
  styleUrl: './sales-history.scss',
})
export class SalesHistory {
  salesService = inject(SalesService);

  columns: DataTableColumn<Sale>[] = [
    { key: 'folio', header: 'N°', cell: (s) => s.folio, sortable: true },
    { key: 'date', header: 'Fecha', cell: (s) => new Date(s.date).toLocaleString('es-EC'), sortable: true },
    { key: 'customerName', header: 'Cliente', cell: (s) => s.customerName, sortable: true },
    { key: 'total', header: 'Total', cell: (s) => `$${s.total.toFixed(2)}`, align: 'right' },
    { key: 'paymentMethod', header: 'Método de pago', cell: (s) => PAYMENT_LABELS[s.paymentMethod] },
    { key: 'status', header: 'Estado', cell: (s) => (s.status === 'completada' ? 'Completada' : 'Anulada') },
    { key: 'createdBy', header: 'Usuario', cell: (s) => s.createdBy },
  ];
}
