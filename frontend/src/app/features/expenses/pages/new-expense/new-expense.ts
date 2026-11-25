import { Component, inject, signal } from '@angular/core';
import { AbstractControl, FormBuilder, ReactiveFormsModule, ValidationErrors, Validators } from '@angular/forms';
import { Router } from '@angular/router';
import { ExpensesService } from '../../services/expenses.service';
import { SuppliersApiService } from '../../services/suppliers-api.service';
import { ExpensePaymentMethod } from '../../models/expense.model';
import { ToastService } from '../../../../core/services/toast.service';
import { PageHeader } from '../../../../shared/components/page-header/page-header';
import { Button } from '../../../../shared/components/button/button';
import { Card } from '../../../../shared/components/card/card';
import { FormField } from '../../../../shared/components/form-field/form-field';

const RUC_PATTERN = /^\d{10}(\d{3})?$/;

/** El proveedor es opcional, pero si se escribe el RUC o la cédula hace falta también el nombre. */
function supplierPair(group: AbstractControl): ValidationErrors | null {
  const ruc = (group.get('providerRuc')?.value as string).trim();
  const name = (group.get('providerName')?.value as string).trim();
  if (!ruc && !name) return null;
  if (!RUC_PATTERN.test(ruc)) return { providerRuc: true };
  return name ? null : { providerName: true };
}

@Component({
  selector: 'app-new-expense',
  imports: [ReactiveFormsModule, PageHeader, Button, Card, FormField],
  templateUrl: './new-expense.html',
  styleUrl: './new-expense.scss',
})
export class NewExpense {
  private expensesService = inject(ExpensesService);
  private suppliersApi = inject(SuppliersApiService);
  private toast = inject(ToastService);
  private router = inject(Router);
  private fb = inject(FormBuilder);

  categories = this.expensesService.categories;
  submitting = signal(false);

  form = this.fb.nonNullable.group(
    {
      date: [new Date().toISOString().slice(0, 10), Validators.required],
      category: ['', Validators.required],
      providerRuc: [''],
      providerName: [''],
      total: [0, [Validators.required, Validators.min(0.01)]],
      paymentMethod: ['efectivo' as ExpensePaymentMethod, Validators.required],
      description: ['', Validators.required],
      receiptNumber: [''],
    },
    { validators: supplierPair },
  );

  constructor() {
    this.expensesService.loadCategories().subscribe((categories) => {
      if (!this.form.controls.category.value && categories.length) {
        this.form.controls.category.setValue(categories[0].name);
      }
    });
  }

  /** Al escribir un RUC o cédula completo, autocompleta el nombre si el proveedor ya existe. */
  onSupplierIdChange(): void {
    const ruc = this.form.controls.providerRuc.value.trim();
    if (!RUC_PATTERN.test(ruc)) return;

    this.suppliersApi.lookup(ruc).subscribe({
      next: (supplier) => {
        if (supplier && this.form.controls.providerRuc.value.trim() === ruc) {
          this.form.controls.providerName.setValue(supplier.name);
        }
      },
      error: () => undefined,
    });
  }

  save(): void {
    if (this.form.invalid || this.submitting()) {
      this.form.markAllAsTouched();
      return;
    }
    const raw = this.form.getRawValue();
    this.submitting.set(true);

    this.expensesService
      .createExpense({
        // Sin zona horaria el backend toma la hora de Ecuador.
        date: `${raw.date}T12:00:00`,
        category: raw.category,
        providerName: raw.providerName,
        providerRuc: raw.providerRuc,
        total: raw.total,
        paymentMethod: raw.paymentMethod,
        description: raw.description,
        receiptNumber: raw.receiptNumber || undefined,
      })
      .subscribe({
        next: () => {
          this.toast.success('Gasto registrado.');
          this.router.navigateByUrl('/expenses/history');
        },
        // El interceptor ya mostró el motivo del error.
        error: () => this.submitting.set(false),
      });
  }
}
