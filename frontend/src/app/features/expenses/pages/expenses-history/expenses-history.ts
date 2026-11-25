import { Component, computed, inject, signal } from '@angular/core';
import { FormBuilder, FormsModule, ReactiveFormsModule, Validators } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { ExpensesService, expenseDay } from '../../services/expenses.service';
import { Expense, ExpensePaymentMethod } from '../../models/expense.model';
import { AuthService } from '../../../../core/services/auth.service';
import { ToastService } from '../../../../core/services/toast.service';
import { PageHeader } from '../../../../shared/components/page-header/page-header';
import { Button } from '../../../../shared/components/button/button';
import { DataTable, DataTableColumn } from '../../../../shared/components/data-table/data-table';
import { Modal } from '../../../../shared/components/modal/modal';
import { StatusBadge } from '../../../../shared/components/status-badge/status-badge';
import { FormField } from '../../../../shared/components/form-field/form-field';

const RUC_PATTERN = /^(\d{10}|\d{13})?$/;

const PAYMENT_LABELS: Record<ExpensePaymentMethod, string> = {
  efectivo: 'Efectivo',
  tarjeta_debito: 'Tarjeta de débito',
  tarjeta_credito: 'Tarjeta de crédito',
  transferencia: 'Transferencia',
  cheque: 'Cheque',
};

@Component({
  selector: 'app-expenses-history',
  imports: [FormsModule, ReactiveFormsModule, RouterLink, PageHeader, Button, DataTable, Modal, StatusBadge, FormField],
  templateUrl: './expenses-history.html',
  styleUrl: './expenses-history.scss',
})
export class ExpensesHistory {
  expensesService = inject(ExpensesService);
  private auth = inject(AuthService);
  private toast = inject(ToastService);
  private fb = inject(FormBuilder);

  readonly isAdmin = this.auth.isAdmin;
  readonly paymentLabels = PAYMENT_LABELS;
  readonly paymentMethods = Object.entries(PAYMENT_LABELS) as [ExpensePaymentMethod, string][];
  readonly categories = this.expensesService.categories;
  readonly trackById = (row: Expense): string => row.id;

  loading = signal(true);
  busy = signal(false);
  selectedId = signal<string | null>(null);
  voiding = signal(false);
  voidReason = signal('');
  editing = signal(false);

  editForm = this.fb.nonNullable.group({
    date: ['', Validators.required],
    categoryId: [0, [Validators.required, Validators.min(1)]],
    providerRuc: ['', Validators.pattern(RUC_PATTERN)],
    providerName: [''],
    total: [0, [Validators.required, Validators.min(0.01)]],
    paymentMethod: ['efectivo' as ExpensePaymentMethod, Validators.required],
    description: ['', [Validators.required, Validators.maxLength(1000)]],
    receiptNumber: ['', Validators.maxLength(50)],
  });

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
    this.editing.set(false);
  }

  startEdit(expense: Expense): void {
    if (!this.categories().length) this.expensesService.loadCategories().subscribe();
    this.cancelVoid();
    this.editForm.reset({
      date: expenseDay(expense.date),
      categoryId: expense.categoryId,
      providerRuc: expense.providerRuc,
      providerName: expense.providerName,
      total: expense.total,
      paymentMethod: expense.paymentMethod,
      description: expense.description,
      receiptNumber: expense.receiptNumber ?? '',
    });
    this.editing.set(true);
  }

  /** Mensaje de error de un campo del formulario de edición (solo después de tocarlo). */
  editError(name: keyof typeof this.editForm.controls): string | null {
    const control = this.editForm.controls[name];
    if (!control.touched || control.valid) return null;
    if (control.hasError('required')) return 'Este campo es obligatorio.';
    if (control.hasError('min')) return 'Debe ser mayor que cero.';
    if (control.hasError('pattern')) return 'Debe tener 10 dígitos (cédula) o 13 (RUC).';
    return 'Valor demasiado largo.';
  }

  /** Guarda solo lo que cambió. Con RUC o cédula, el proveedor se busca o se crea. */
  saveEdit(expense: Expense): void {
    if (this.busy()) return;
    const value = this.editForm.getRawValue();
    if (value.providerRuc.trim() && !value.providerName.trim()) {
      this.editForm.controls.providerName.setErrors({ required: true });
    }
    if (this.editForm.invalid) {
      this.editForm.markAllAsTouched();
      return;
    }
    this.busy.set(true);
    this.expensesService.updateExpense(expense, { ...value, categoryId: Number(value.categoryId) }).subscribe({
      next: (saved) => {
        this.busy.set(false);
        this.editing.set(false);
        if (saved) this.toast.success('Gasto actualizado.');
      },
      // El interceptor ya mostró el motivo del error.
      error: () => this.busy.set(false),
    });
  }

  startVoid(): void {
    this.editing.set(false);
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
