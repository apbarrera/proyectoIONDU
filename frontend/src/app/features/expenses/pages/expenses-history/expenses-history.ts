import { Component, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { ExpensesService } from '../../services/expenses.service';
import { Expense, ExpensePaymentMethod } from '../../models/expense.model';
import { AuthService } from '../../../../core/services/auth.service';
import { ToastService } from '../../../../core/services/toast.service';
import { PageHeader } from '../../../../shared/components/page-header/page-header';
import { Button } from '../../../../shared/components/button/button';
import { DataTable, DataTableColumn } from '../../../../shared/components/data-table/data-table';
import { Modal } from '../../../../shared/components/modal/modal';
import { StatusBadge } from '../../../../shared/components/status-badge/status-badge';
import { FormField } from '../../../../shared/components/form-field/form-field';

const PAYMENT_LABELS: Record<ExpensePaymentMethod, string> = {
  efectivo: 'Efectivo',
  tarjeta_debito: 'Tarjeta de débito',
  tarjeta_credito: 'Tarjeta de crédito',
  transferencia: 'Transferencia',
  cheque: 'Cheque',
};

@Component({
  selector: 'app-expenses-history',
  imports: [FormsModule, RouterLink, PageHeader, Button, DataTable, Modal, StatusBadge, FormField],
  templateUrl: './expenses-history.html',
  styleUrl: './expenses-history.scss',
})
export class ExpensesHistory {
  expensesService = inject(ExpensesService);
  private auth = inject(AuthService);
  private toast = inject(ToastService);

  readonly isAdmin = this.auth.isAdmin;
  readonly paymentLabels = PAYMENT_LABELS;
  readonly trackById = (row: Expense): string => row.id;

  loading = signal(true);
  busy = signal(false);
  selectedId = signal<string | null>(null);
  voiding = signal(false);
  voidReason = signal('');

  selected = computed(() => this.expensesService.expenses().find((e) => e.id === this.selectedId()) ?? null);

  columns: DataTableColumn<Expense>[] = [
    { key: 'date', header: 'Fecha', cell: (e) => this.formatDate(e.date), sortable: true },
    { key: 'providerName', header: 'Proveedor', cell: (e) => e.providerName || '—', sortable: true },
    { key: 'category', header: 'Categoría', cell: (e) => e.category },
    { key: 'description', header: 'Descripción', cell: (e) => e.description },
    { key: 'total', header: 'Monto', cell: (e) => `$${e.total.toFixed(2)}`, align: 'right' },
    { key: 'sourceType', header: 'Origen', cell: (e) => (e.sourceType === 'email' ? 'Correo' : 'Manual') },
    {
      key: 'status',
      header: 'Estado',
      cell: (e) => (e.status === 'anulado' ? 'Anulado' : 'Registrado'),
      badge: (e) =>
        e.status === 'anulado' ? { label: 'Anulado', tone: 'danger' } : { label: 'Registrado', tone: 'success' },
    },
  ];

  constructor() {
    this.expensesService.getExpenses().subscribe({
      next: () => this.loading.set(false),
      error: () => this.loading.set(false),
    });
  }

  formatDate(iso: string): string {
    return new Date(iso).toLocaleDateString('es-EC');
  }

  open(row: Expense): void {
    this.selectedId.set(row.id);
  }

  close(): void {
    this.selectedId.set(null);
    this.cancelVoid();
  }

  startVoid(): void {
    this.voidReason.set('');
    this.voiding.set(true);
  }

  cancelVoid(): void {
    this.voiding.set(false);
    this.voidReason.set('');
  }

  /** Anula el gasto (solo Administrador): deja de contar en los totales y queda en el historial. */
  confirmVoid(row: Expense): void {
    const reason = this.voidReason().trim();
    if (this.busy() || reason.length < 3) return;
    this.busy.set(true);
    this.expensesService.voidExpense(row.id, reason).subscribe({
      next: () => {
        this.busy.set(false);
        this.cancelVoid();
        this.toast.success('Gasto anulado.');
      },
      // El interceptor ya mostró el motivo del error.
      error: () => this.busy.set(false),
    });
  }
}
