import { Component, computed, inject, signal } from '@angular/core';
import { toSignal } from '@angular/core/rxjs-interop';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { ProductsService } from '../../services/products.service';
import { Product, ProductType } from '../../models/product.model';
import {
  ImportFormat,
  ImportParseResult,
  buildTemplateCsv,
  buildTemplateXlsx,
  readImportFile,
} from '../../utils/product-import.util';
import { PageHeader } from '../../../../shared/components/page-header/page-header';
import { Button } from '../../../../shared/components/button/button';
import { DataTable, DataTableColumn } from '../../../../shared/components/data-table/data-table';
import { Modal } from '../../../../shared/components/modal/modal';
import { FormField } from '../../../../shared/components/form-field/form-field';
import { Icon } from '../../../../shared/components/icon/icon';
import { ToastService } from '../../../../core/services/toast.service';

const TYPE_LABELS: Record<ProductType, string> = {
  simple: 'Producto',
  insumo: 'Insumo',
};

const UNIT_SUGGESTIONS = ['unidad', 'kg', 'g', 'L', 'ml', 'caja', 'paquete', 'docena'];

/** Cuántas filas válidas se muestran en la vista previa de la carga masiva. */
const PREVIEW_ROWS = 6;
/** Cuántos errores se listan antes de resumir el resto. */
const MAX_LISTED_ERRORS = 15;

@Component({
  selector: 'app-products',
  imports: [ReactiveFormsModule, PageHeader, Button, DataTable, Modal, FormField, Icon],
  templateUrl: './products.html',
  styleUrl: './products.scss',
})
export class Products {
  private productsService = inject(ProductsService);
  private toast = inject(ToastService);
  private fb = inject(FormBuilder);

  typeLabels = TYPE_LABELS;
  unitSuggestions = UNIT_SUGGESTIONS;
  categories = this.productsService.categories;
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

  // --- Elegir cómo agregar ---
  chooserOpen = signal(false);

  openNew(): void {
    this.chooserOpen.set(true);
  }

  chooseSingle(): void {
    this.chooserOpen.set(false);
    this.openCreate();
  }

  chooseBulk(): void {
    this.chooserOpen.set(false);
    this.openImport();
  }

  // --- Producto individual ---
  formOpen = signal(false);
  editingId = signal<string | null>(null);
  skuTaken = signal(false);

  form = this.fb.nonNullable.group({
    sku: [''],
    name: ['', Validators.required],
    category: ['', Validators.required],
    type: ['simple' as ProductType, Validators.required],
    unit: ['unidad', Validators.required],
    salePrice: [0],
    cost: [0, Validators.required],
    currentStock: [0, Validators.required],
    minStock: [0, Validators.required],
  });

  private selectedType = toSignal(this.form.controls.type.valueChanges, { initialValue: 'simple' as ProductType });

  /** Código que recibirá el producto si se deja el campo vacío. */
  skuPlaceholder = computed(() => `Automático (${this.productsService.nextSku(this.selectedType())})`);

  openCreate(): void {
    this.editingId.set(null);
    this.skuTaken.set(false);
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
    this.skuTaken.set(false);
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
    const id = this.editingId();
    const sku = raw.sku.trim();

    const taken = this.productsService
      .products()
      .some((p) => p.id !== id && p.sku.toLowerCase() === sku.toLowerCase());
    if (sku && taken) {
      this.skuTaken.set(true);
      return;
    }

    const payload = {
      ...raw,
      sku,
      category: raw.category.trim(),
      salePrice: raw.type === 'insumo' ? null : raw.salePrice,
      active: true,
    };

    if (id) {
      // Al editar, un código vaciado conserva el que ya tenía.
      const current = this.productsService.getProduct(id);
      this.productsService.updateProduct(id, { ...payload, sku: sku || current?.sku || '' }).subscribe(() => {
        this.toast.success('Producto actualizado.');
        this.formOpen.set(false);
      });
    } else {
      this.productsService.createProduct(payload).subscribe((created) => {
        this.toast.success(`Producto creado con código ${created.sku}.`);
        this.formOpen.set(false);
      });
    }
  }

  close(): void {
    this.formOpen.set(false);
  }

  // --- Carga masiva ---
  importOpen = signal(false);
  importFormat = signal<ImportFormat>('xlsx');
  importResult = signal<ImportParseResult | null>(null);
  importFileName = signal('');
  reading = signal(false);

  validRows = computed(() => (this.importResult()?.rows ?? []).filter((r) => r.product));
  invalidRows = computed(() => (this.importResult()?.rows ?? []).filter((r) => !r.product));
  previewRows = computed(() => this.validRows().slice(0, PREVIEW_ROWS));
  listedErrors = computed(() => this.invalidRows().slice(0, MAX_LISTED_ERRORS));
  hiddenErrorCount = computed(() => Math.max(0, this.invalidRows().length - MAX_LISTED_ERRORS));
  acceptedFiles = computed(() => (this.importFormat() === 'csv' ? '.csv,text/csv' : '.xlsx'));

  openImport(): void {
    this.importFormat.set('xlsx');
    this.resetImportFile();
    this.importOpen.set(true);
  }

  closeImport(): void {
    this.importOpen.set(false);
  }

  setFormat(format: ImportFormat, fileInput: HTMLInputElement): void {
    this.importFormat.set(format);
    fileInput.value = '';
    this.resetImportFile();
  }

  private resetImportFile(): void {
    this.importResult.set(null);
    this.importFileName.set('');
  }

  async downloadTemplate(): Promise<void> {
    if (this.importFormat() === 'csv') {
      this.download(new Blob([buildTemplateCsv()], { type: 'text/csv;charset=utf-8' }), 'plantilla-productos.csv');
    } else {
      this.download(await buildTemplateXlsx(), 'plantilla-productos.xlsx');
    }
  }

  async onFileSelected(event: Event): Promise<void> {
    const file = (event.target as HTMLInputElement).files?.[0];
    if (!file) {
      this.resetImportFile();
      return;
    }
    this.importFileName.set(file.name);
    this.importResult.set(null);
    this.reading.set(true);
    const existing = this.productsService.products().map((p) => p.sku);
    this.importResult.set(await readImportFile(file, this.importFormat(), existing));
    this.reading.set(false);
  }

  confirmImport(): void {
    const products = this.validRows().map((r) => r.product!);
    if (products.length === 0) return;
    this.productsService.createMany(products).subscribe((created) => {
      const skipped = this.invalidRows().length;
      const base = `Se importaron ${created.length} ${created.length === 1 ? 'producto' : 'productos'}.`;
      if (skipped > 0) this.toast.warning(`${base} ${skipped} ${skipped === 1 ? 'fila se omitió' : 'filas se omitieron'} por errores.`);
      else this.toast.success(base);
      this.importOpen.set(false);
    });
  }

  private download(blob: Blob, fileName: string): void {
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = fileName;
    document.body.appendChild(link);
    link.click();
    link.remove();
    setTimeout(() => URL.revokeObjectURL(url));
  }
}
