import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { finalize, forkJoin } from 'rxjs';

import { Product, ProductType } from '../../models/product.model';
import {
  CreateProductInput,
  ProductCategory,
  ProductsApiService,
  UpdateProductInput,
} from '../../services/products-api.service';
import { PageHeader } from '../../../../shared/components/page-header/page-header';
import { Button } from '../../../../shared/components/button/button';
import { DataTable, DataTableColumn } from '../../../../shared/components/data-table/data-table';
import { Modal } from '../../../../shared/components/modal/modal';
import { FormField } from '../../../../shared/components/form-field/form-field';
import { ToastService } from '../../../../core/services/toast.service';

const TYPE_LABELS: Record<ProductType, string> = {
  venta: 'Producto para venta',
  insumo: 'Insumo',
  ambos: 'Venta e insumo',
};

@Component({
  selector: 'app-products',
  imports: [ReactiveFormsModule, PageHeader, Button, DataTable, Modal, FormField],
  templateUrl: './products.html',
  styleUrl: './products.scss',
})
export class Products implements OnInit {
  private readonly api = inject(ProductsApiService);
  private readonly toast = inject(ToastService);
  private readonly fb = inject(FormBuilder);

  readonly typeLabels = TYPE_LABELS;
  readonly typeFilter = signal<ProductType | 'todos'>('todos');
  readonly products = signal<Product[]>([]);
  readonly categories = signal<ProductCategory[]>([]);
  readonly loading = signal(true);
  readonly saving = signal(false);
  readonly creatingCategory = signal(false);
  readonly categoryFormOpen = signal(false);
  readonly formOpen = signal(false);
  readonly editingId = signal<string | null>(null);

  readonly filteredProducts = computed(() => {
    const filter = this.typeFilter();
    const list = this.products();
    return filter === 'todos' ? list : list.filter((product) => product.type === filter);
  });

  readonly columns: DataTableColumn<Product>[] = [
    { key: 'sku', header: 'Código', cell: (product) => product.sku, sortable: true },
    { key: 'name', header: 'Nombre', cell: (product) => product.name, sortable: true },
    { key: 'category', header: 'Categoría', cell: (product) => product.category },
    { key: 'type', header: 'Tipo', cell: (product) => TYPE_LABELS[product.type] },
    { key: 'stock', header: 'Stock', cell: (product) => `${product.currentStock} ${product.unit}`, align: 'right' },
    { key: 'minStock', header: 'Stock mínimo', cell: (product) => `${product.minStock} ${product.unit}`, align: 'right' },
    {
      key: 'price',
      header: 'Precio',
      cell: (product) => (product.salePrice != null ? `$${product.salePrice.toFixed(2)}` : '—'),
      align: 'right',
    },
    { key: 'active', header: 'Estado', cell: (product) => product.active ? 'Activo' : 'Inactivo' },
  ];

  readonly form = this.fb.nonNullable.group({
    sku: ['', Validators.required],
    name: ['', Validators.required],
    description: [''],
    categoryId: [0, [Validators.required, Validators.min(1)]],
    type: ['venta' as ProductType, Validators.required],
    unit: ['UNIDAD', Validators.required],
    salePrice: [0, [Validators.min(0)]],
    cost: [0, [Validators.required, Validators.min(0)]],
    currentStock: [0, [Validators.required, Validators.min(0)]],
    minStock: [0, [Validators.required, Validators.min(0)]],
    active: [true],
  });

  readonly categoryForm = this.fb.nonNullable.group({
    name: ['', [Validators.required, Validators.maxLength(100)]],
  });

  ngOnInit(): void {
    this.loadCatalog();
  }

  loadCatalog(): void {
    this.loading.set(true);

    forkJoin({
      products: this.api.getProducts(),
      categories: this.api.getCategories(),
    })
      .pipe(finalize(() => this.loading.set(false)))
      .subscribe(({ products, categories }) => {
        this.products.set(products);
        this.categories.set(categories);
      });
  }

  openCreate(): void {
    this.editingId.set(null);
    this.categoryFormOpen.set(false);
    this.form.reset({
      sku: '',
      name: '',
      description: '',
      categoryId: this.categories()[0]?.id ?? 0,
      type: 'venta',
      unit: 'UNIDAD',
      salePrice: 0,
      cost: 0,
      currentStock: 0,
      minStock: 0,
      active: true,
    });
    this.formOpen.set(true);
  }

  openEdit(product: Product): void {
    this.editingId.set(product.id);
    this.categoryFormOpen.set(false);

    const categoryId = product.categoryId ??
      this.categories().find((category) => category.name === product.category)?.id ?? 0;

    this.form.reset({
      sku: product.sku,
      name: product.name,
      description: product.description ?? '',
      categoryId,
      type: product.type,
      unit: product.unit,
      salePrice: product.salePrice ?? 0,
      cost: product.cost,
      currentStock: product.currentStock,
      minStock: product.minStock,
      active: product.active,
    });

    this.formOpen.set(true);
  }

  toggleCategoryForm(): void {
    this.categoryFormOpen.update((open) => !open);
    this.categoryForm.reset({ name: '' });
  }

  createCategory(): void {
    if (this.categoryForm.invalid || this.creatingCategory()) {
      this.categoryForm.markAllAsTouched();
      return;
    }

    const name = this.categoryForm.controls.name.value.trim();
    if (!name) return;

    this.creatingCategory.set(true);
    this.api.createCategory(name)
      .pipe(finalize(() => this.creatingCategory.set(false)))
      .subscribe((category) => {
        this.categories.update((items) => [...items, category].sort((a, b) => a.name.localeCompare(b.name)));
        this.form.controls.categoryId.setValue(category.id);
        this.categoryFormOpen.set(false);
        this.categoryForm.reset({ name: '' });
        this.toast.success('Categoría creada.');
      });
  }

  save(): void {
    if (this.form.invalid || this.saving()) {
      this.form.markAllAsTouched();
      return;
    }

    const raw = this.form.getRawValue();
    const input = {
      sku: raw.sku.trim(),
      name: raw.name.trim(),
      description: raw.description.trim() || null,
      categoryId: raw.categoryId,
      type: raw.type,
      unit: raw.unit.trim(),
      salePrice: raw.type === 'insumo' ? null : raw.salePrice,
      cost: raw.cost,
      minStock: raw.minStock,
    };

    if (!input.sku || !input.name || !input.unit || input.categoryId <= 0) return;

    this.saving.set(true);
    const id = this.editingId();

    if (id) {
      const update: UpdateProductInput = {
        ...input,
        active: raw.active,
      };

      this.api.updateProduct(id, update)
        .pipe(finalize(() => this.saving.set(false)))
        .subscribe((updated) => {
          this.products.update((items) => items.map((item) => item.id === id ? updated : item));
          this.toast.success('Producto actualizado.');
          this.close();
        });
    } else {
      const create: CreateProductInput = {
        ...input,
        currentStock: raw.currentStock,
      };

      this.api.createProduct(create)
        .pipe(finalize(() => this.saving.set(false)))
        .subscribe((created) => {
          this.products.update((items) => [created, ...items]);
          this.toast.success('Producto creado.');
          this.close();
        });
    }
  }

  close(): void {
    this.formOpen.set(false);
    this.categoryFormOpen.set(false);
  }
}