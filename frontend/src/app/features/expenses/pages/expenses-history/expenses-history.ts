import { Component, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import { ExpensesService } from '../../services/expenses.service';
import { Expense } from '../../models/expense.model';
import { PageHeader } from '../../../../shared/components/page-header/page-header';
import { Button } from '../../../../shared/components/button/button';
import { DataTable, DataTableColumn } from '../../../../shared/components/data-table/data-table';

@Component({
  selector: 'app-expenses-history',
  imports: [RouterLink, PageHeader, Button, DataTable],
  templateUrl: './expenses-history.html',
  styleUrl: './expenses-history.scss',
})
export class ExpensesHistory {
  expensesService = inject(ExpensesService);

  loading = signal(true);

  columns: DataTableColumn<Expense>[] = [
    { key: 'date', header: 'Fecha', cell: (e) => new Date(e.date).toLocaleDateString('es-EC'), sortable: true },
    { key: 'providerName', header: 'Proveedor', cell: (e) => e.providerName || '—', sortable: true },
    { key: 'category', header: 'Categoría', cell: (e) => e.category },
    { key: 'description', header: 'Descripción', cell: (e) => e.description },
    { key: 'total', header: 'Monto', cell: (e) => `$${e.total.toFixed(2)}`, align: 'right' },
    { key: 'sourceType', header: 'Origen', cell: (e) => (e.sourceType === 'email' ? 'Correo' : 'Manual') },
  ];

  constructor() {
    this.expensesService.getExpenses().subscribe({
      next: () => this.loading.set(false),
      error: () => this.loading.set(false),
    });
  }
}
