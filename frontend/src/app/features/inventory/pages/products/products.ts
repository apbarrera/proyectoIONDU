import { Component, computed, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { ProductsService } from '../../services/products.service';
import { Product, ProductType } from '../../models/product.model';
import { PageHeader } from '../../../../shared/components/page-header/page-header';
import { Button } from '../../../../shared/components/button/button';
import { DataTable, DataTableColumn } from '../../../../shared/components/data-table/data-table';
import { Modal } from '../../../../shared/components/modal/modal';
import { FormField } from '../../../../shared/components/form-field/form-field';
import { ToastService } from '../../../../core/services/toast.service';

const TYPE_LABELS: Record<ProductType, string> = {
  simple: 'Producto simple',
  insumo: 'Insumo',
  compuesto: 'Producto compuesto',
};

@Component({
  selector: 'app-products',
  imports: [ReactiveFormsModule, PageHeader, Button, DataTable, Modal, FormField],
  templateUrl: './products.html',
  styleUrl: './products.scss',
})
export class Products {
  private productsService = inject(ProductsService);
  private toast = inject(ToastService);
  private fb = inject(FormBuilder);

  typeLabels = TYPE_LABELS;
  typeFilter = signal<ProductType | 'todos'>('todos');

  filteredProducts = computed(() => {
    const filter = this.typeFilter();
    const list = this.productsService.products();
    return filter === 'todos' ? list : list.filter((p) => p.type === filter);
  });

  columns: DataTableColumn<Product>[] = [
    { key: 'sku', header: 'Código', cell: (p) => p.sku, sortable: true },
    { key: 'name', header: 'Nombre', cell: (p) => p.name, sortable: true },
    { key: 'category', header: 'Categoría', cell: (p) => p.category },
    { key: 'type', header: 'Tipo', cell: (p) => TYPE_LABELS[p.type] },
    { key: 'stock', header: 'Stock', cell: (p) => `${p.currentStock} ${p.unit}`, align: 'right' },
    { key: 'minStock', header: 'Stock mínimo', cell: (p) => `${p.minStock} ${p.unit}`, align: 'right' },
    {
      key: 'price',
      header: 'Precio',
      cell: (p) => (p.salePrice != null ? `$${p.salePrice.toFixed(2)}` : '—'),
      align: 'right',
    },
  ];

  formOpen = signal(false);
  editingId = signal<string | null>(null);

  form = this.fb.nonNullable.group({
    sku: ['', Validators.required],
    name: ['', Validators.required],
    category: ['', Validators.required],
    type: ['simple' as ProductType, Validators.required],
    unit: ['unidad', Validators.required],
    salePrice: [0],
    cost: [0, Validators.required],
    currentStock: [0, Validators.required],
    minStock: [0, Validators.required],
  });

  openCreate(): void {
    this.editingId.set(null);
    this.form.reset({
      sku: '',
      name: '',
      category: '',
      type: 'simple',
      unit: 'unidad',
      salePrice: 0,
      cost: 0,
      currentStock: 0,
      minStock: 0,
    });
    this.formOpen.set(true);
  }

  openEdit(product: Product): void {
    this.editingId.set(product.id);
    this.form.reset({
      sku: product.sku,
      name: product.name,
      category: product.category,
      type: product.type,
      unit: product.unit,
      salePrice: product.salePrice ?? 0,
      cost: product.cost,
      currentStock: product.currentStock,
      minStock: product.minStock,
    });
    this.formOpen.set(true);
  }

  save(): void {
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }
    const raw = this.form.getRawValue();
    const payload = { ...raw, salePrice: raw.type === 'insumo' ? null : raw.salePrice, active: true };

    const id = this.editingId();
    if (id) {
      this.productsService.updateProduct(id, payload).subscribe(() => {
        this.toast.success('Producto actualizado.');
        this.formOpen.set(false);
      });
    } else {
      this.productsService.createProduct(payload).subscribe(() => {
        this.toast.success('Producto creado.');
        this.formOpen.set(false);
      });
    }
  }

  close(): void {
    this.formOpen.set(false);
  }
}
