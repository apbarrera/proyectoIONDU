import { Component, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { AdjustmentsService } from '../../services/adjustments.service';
import { ProductsService } from '../../services/products.service';
import { StockAdjustment } from '../../models/adjustment.model';
import { PageHeader } from '../../../../shared/components/page-header/page-header';
import { Button } from '../../../../shared/components/button/button';
import { Card } from '../../../../shared/components/card/card';
import { DataTable, DataTableColumn } from '../../../../shared/components/data-table/data-table';
import { ConfirmDialogService } from '../../../../core/services/confirm-dialog.service';
import { ToastService } from '../../../../core/services/toast.service';

@Component({
  selector: 'app-adjustments',
  imports: [FormsModule, PageHeader, Button, Card, DataTable],
  templateUrl: './adjustments.html',
  styleUrl: './adjustments.scss',
})
export class Adjustments {
  productsService = inject(ProductsService);
  adjustmentsService = inject(AdjustmentsService);
  private confirmDialog = inject(ConfirmDialogService);
  private toast = inject(ToastService);

  selectedProductId = signal('');
  newStock = signal(0);
  reason = signal('');

  selectedProduct = computed(() => this.productsService.getProduct(this.selectedProductId()));
  difference = computed(() => {
    const product = this.selectedProduct();
    if (!product) return 0;
    return Math.round((this.newStock() - product.currentStock) * 1000) / 1000;
  });

  columns: DataTableColumn<StockAdjustment>[] = [
    { key: 'date', header: 'Fecha', cell: (a) => new Date(a.date).toLocaleString('es-EC'), sortable: true },
    { key: 'productName', header: 'Producto', cell: (a) => a.productName, sortable: true },
    { key: 'previousStock', header: 'Stock anterior', cell: (a) => `${a.previousStock}`, align: 'right' },
    { key: 'newStock', header: 'Stock nuevo', cell: (a) => `${a.newStock}`, align: 'right' },
    { key: 'reason', header: 'Motivo', cell: (a) => a.reason },
    { key: 'createdBy', header: 'Usuario', cell: (a) => a.createdBy },
  ];

  onProductChange(id: string): void {
    this.selectedProductId.set(id);
    this.newStock.set(this.productsService.getProduct(id)?.currentStock ?? 0);
  }

  submit(): void {
    const product = this.selectedProduct();
    if (!product || !this.reason().trim()) {
      this.toast.warning('Selecciona un producto e indica el motivo del ajuste.');
      return;
    }

    this.confirmDialog
      .confirm({
        title: 'Confirmar ajuste de inventario',
        message: `¿Ajustar el stock de "${product.name}" de ${product.currentStock} a ${this.newStock()} ${product.unit}?`,
      })
      .subscribe((confirmed) => {
        if (!confirmed) return;
        this.adjustmentsService.createAdjustment(product.id, this.newStock(), this.reason()).subscribe(() => {
          this.toast.success('Ajuste registrado.');
          this.reason.set('');
        });
      });
  }
}
