import { Component, computed, inject, signal } from '@angular/core';
import { AbstractControl, FormBuilder, ReactiveFormsModule, ValidationErrors, Validators } from '@angular/forms';
import { Router } from '@angular/router';
import { ExpensesService, PurchaseItem } from '../../services/expenses.service';
import { SuppliersApiService } from '../../services/suppliers-api.service';
import { ExpensePaymentMethod } from '../../models/expense.model';
import { ProductsApiService } from '../../../inventory/services/products-api.service';
import { Product } from '../../../inventory/models/product.model';
import { ToastService } from '../../../../core/services/toast.service';
import { PageHeader } from '../../../../shared/components/page-header/page-header';
import { Button } from '../../../../shared/components/button/button';
import { Card } from '../../../../shared/components/card/card';
import { FormField } from '../../../../shared/components/form-field/form-field';
import { Icon } from '../../../../shared/components/icon/icon';
import { Switch } from '../../../../shared/components/switch/switch';

/** Fila de la compra en el formulario: el producto puede no estar elegido todavía. */
interface PurchaseRow {
  key: number;
  productId: string;
  quantity: number | null;
  unitCost: number | null;
}

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
  imports: [ReactiveFormsModule, PageHeader, Button, Card, FormField, Icon, Switch],
  templateUrl: './new-expense.html',
  styleUrl: './new-expense.scss',
})
export class NewExpense {
  private expensesService = inject(ExpensesService);
  private suppliersApi = inject(SuppliersApiService);
  private toast = inject(ToastService);
  private router = inject(Router);
  private fb = inject(FormBuilder);

  private productsApi = inject(ProductsApiService);

  categories = this.expensesService.categories;
  submitting = signal(false);

  /** RF-4.4: la compra también suma al stock de los productos elegidos. */
  addsStock = signal(false);
  products = signal<Product[]>([]);
  rows = signal<PurchaseRow[]>([]);
  #nextKey = 1;

  /** Mensaje del primer problema de la compra, o '' si se puede guardar. */
  purchaseError = computed(() => {
    if (!this.addsStock()) return '';
    const rows = this.rows();
    if (!rows.length) return 'Agrega al menos un producto o desactiva "Suma al inventario".';
    if (rows.some((r) => !r.productId)) return 'Elige el producto de cada fila.';
    if (rows.some((r) => !r.quantity || r.quantity <= 0)) return 'La cantidad debe ser mayor que 0.';
    if (rows.some((r) => r.unitCost != null && r.unitCost < 0)) return 'El costo unitario no puede ser negativo.';
    const ids = rows.map((r) => r.productId);
    if (new Set(ids).size !== ids.length) return 'Un producto no puede repetirse en la compra.';
    return '';
  });

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

  /** Al activar "Suma al inventario" carga los productos y deja una fila lista. */
  toggleAddsStock(on: boolean): void {
    this.addsStock.set(on);
    if (!on) return;
    if (!this.rows().length) this.addRow();
    if (!this.products().length) {
      this.productsApi.getProducts().subscribe({
        next: (products) => this.products.set(products.filter((p) => p.active)),
        error: () => undefined,
      });
    }
  }

  addRow(): void {
    this.rows.update((rows) => [...rows, { key: this.#nextKey++, productId: '', quantity: 1, unitCost: null }]);
  }

  removeRow(key: number): void {
    this.rows.update((rows) => rows.filter((r) => r.key !== key));
  }

  updateRow(key: number, changes: Partial<Omit<PurchaseRow, 'key'>>): void {
    this.rows.update((rows) => rows.map((r) => (r.key === key ? { ...r, ...changes } : r)));
  }

  /** Lee un número de un input; vacío → null. */
  numberFrom(event: Event): number | null {
    const value = (event.target as HTMLInputElement).value;
    return value === '' ? null : Number(value);
  }

  unitOf(productId: string): string {
    return this.products().find((p) => p.id === productId)?.unit ?? '';
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
    if (this.form.invalid || this.purchaseError() || this.submitting()) {
      this.form.markAllAsTouched();
      return;
    }
    const raw = this.form.getRawValue();
    const items: PurchaseItem[] = this.addsStock()
      ? this.rows().map((r) => ({ productId: r.productId, quantity: r.quantity!, unitCost: r.unitCost }))
      : [];
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
        items,
      })
      .subscribe({
        next: () => {
          this.toast.success(
            items.length ? `Gasto registrado y ${items.length} producto(s) sumados al inventario.` : 'Gasto registrado.',
          );
          this.router.navigateByUrl('/expenses/history');
        },
        // El interceptor ya mostró el motivo del error.
        error: () => this.submitting.set(false),
      });
  }
}
