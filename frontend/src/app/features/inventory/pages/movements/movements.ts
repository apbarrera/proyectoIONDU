import { Component, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { MovementsService } from '../../services/movements.service';
import { ProductsService } from '../../services/products.service';
import { InventoryMovement, MovementType } from '../../models/movement.model';
import { PageHeader } from '../../../../shared/components/page-header/page-header';
import { Button } from '../../../../shared/components/button/button';
import { Card } from '../../../../shared/components/card/card';
import { DataTable, DataTableColumn } from '../../../../shared/components/data-table/data-table';
import { ToastService } from '../../../../core/services/toast.service';

const TYPE_LABELS: Record<MovementType, string> = {
  entrada: 'Entrada',
  salida: 'Salida',
  ajuste: 'Ajuste',
  venta: 'Venta',
};

@Component({
  selector: 'app-movements',
  imports: [FormsModule, PageHeader, Button, Card, DataTable],
  templateUrl: './movements.html',
  styleUrl: './movements.scss',
})
export class Movements {
  movementsService = inject(MovementsService);
  productsService = inject(ProductsService);
  private toast = inject(ToastService);

  loading = signal(true);
  submitting = signal(false);

  // Formulario de entrada o salida manual (RF-4.3).
  productId = signal('');
  type = signal<'entrada' | 'salida'>('entrada');
  quantity = signal<number | null>(null);
  reason = signal('');

  selectedProduct = computed(() => this.productsService.getProduct(this.productId()));

  canSubmit = computed(
    () => !!this.selectedProduct() && (this.quantity() ?? 0) > 0 && !!this.reason().trim() && !this.submitting(),
  );

  columns: DataTableColumn<InventoryMovement>[] = [
    { key: 'date', header: 'Fecha', cell: (m) => new Date(m.date).toLocaleString('es-EC'), sortable: true },
    { key: 'productName', header: 'Producto', cell: (m) => m.productName, sortable: true },
    { key: 'type', header: 'Tipo', cell: (m) => TYPE_LABELS[m.type] },
    {
      key: 'quantity',
      header: 'Cantidad',
      cell: (m) => `${m.quantity > 0 ? '+' : ''}${m.quantity}`,
      align: 'right',
    },
    { key: 'resultingStock', header: 'Stock resultante', cell: (m) => `${m.resultingStock}`, align: 'right' },
    { key: 'reference', header: 'Motivo', cell: (m) => m.reference },
    { key: 'createdBy', header: 'Usuario', cell: (m) => m.createdBy },
  ];

  constructor() {
    this.productsService.refresh();
    this.movementsService.getMovements().subscribe({
      next: () => this.loading.set(false),
      error: () => this.loading.set(false),
    });
  }

  submit(): void {
    const product = this.selectedProduct();
    const quantity = this.quantity();
    if (!product || !quantity || !this.canSubmit()) return;

    this.submitting.set(true);
    this.movementsService
      .record({
        productId: Number(product.id),
        type: this.type(),
        quantity,
        reason: this.reason().trim(),
      })
      .subscribe({
        next: (movement) => {
          this.toast.success(
            `${TYPE_LABELS[movement.type]} registrada. Stock de ${product.name}: ${movement.resultingStock} ${product.unit}.`,
          );
          this.quantity.set(null);
          this.reason.set('');
          this.submitting.set(false);
          this.productsService.refresh();
        },
        // El interceptor ya mostró el motivo (por ejemplo, stock insuficiente).
        error: () => this.submitting.set(false),
      });
  }
}
