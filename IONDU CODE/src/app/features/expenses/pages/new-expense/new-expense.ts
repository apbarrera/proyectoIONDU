import { Component, computed, inject } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { Router } from '@angular/router';
import { ExpensesService } from '../../services/expenses.service';
import { ToastService } from '../../../../core/services/toast.service';
import { TenantService } from '../../../../core/services/tenant.service';
import { PageHeader } from '../../../../shared/components/page-header/page-header';
import { Button } from '../../../../shared/components/button/button';
import { Card } from '../../../../shared/components/card/card';
import { FormField } from '../../../../shared/components/form-field/form-field';

const CATEGORIES = ['Insumos', 'Servicios', 'Empaques', 'Arriendo', 'Nómina', 'Marketing', 'Otros'];

@Component({
  selector: 'app-new-expense',
  imports: [ReactiveFormsModule, PageHeader, Button, Card, FormField],
  templateUrl: './new-expense.html',
  styleUrl: './new-expense.scss',
})
export class NewExpense {
  private expensesService = inject(ExpensesService);
  private tenant = inject(TenantService);
  private toast = inject(ToastService);
  private router = inject(Router);
  private fb = inject(FormBuilder);

  categories = CATEGORIES;

  form = this.fb.nonNullable.group({
    date: [new Date().toISOString().slice(0, 10), Validators.required],
    category: ['Insumos', Validators.required],
    providerName: ['', Validators.required],
    providerRuc: [''],
    amount: [0, [Validators.required, Validators.min(0.01)]],
    paymentMethod: ['efectivo' as const, Validators.required],
    description: ['', Validators.required],
    observation: [''],
  });

  ivaAmount = computed(() => {
    const amount = this.form.controls.amount.value || 0;
    return Math.round(amount * this.tenant.tenant().ivaRate * 100) / 100;
  });

  total = computed(() => Math.round(((this.form.controls.amount.value || 0) + this.ivaAmount()) * 100) / 100);

  save(): void {
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }
    const raw = this.form.getRawValue();
    const ivaAmount = Math.round(raw.amount * this.tenant.tenant().ivaRate * 100) / 100;

    this.expensesService
      .createExpense({
        date: new Date(raw.date).toISOString(),
        category: raw.category,
        providerName: raw.providerName,
        providerRuc: raw.providerRuc,
        amount: raw.amount,
        ivaAmount,
        total: Math.round((raw.amount + ivaAmount) * 100) / 100,
        paymentMethod: raw.paymentMethod,
        description: raw.description,
        observation: raw.observation || undefined,
        sourceType: 'manual',
      })
      .subscribe(() => {
        this.toast.success('Gasto registrado.');
        this.router.navigateByUrl('/expenses/history');
      });
  }
}
