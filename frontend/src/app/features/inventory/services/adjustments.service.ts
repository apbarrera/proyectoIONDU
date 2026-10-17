import { Injectable, inject, signal } from '@angular/core';
import { Observable, throwError } from 'rxjs';
import { StockAdjustment } from '../models/adjustment.model';
import { simulateRequest } from '../../../core/services/mock-http.util';
import { generateId } from '../../../core/utils/id.util';
import { ProductsService } from './products.service';
import { AuditService } from '../../../core/services/audit.service';
import { AuthService } from '../../../core/services/auth.service';

@Injectable({ providedIn: 'root' })
export class AdjustmentsService {
  private products = inject(ProductsService);
  private audit = inject(AuditService);
  private auth = inject(AuthService);

  #adjustments = signal<StockAdjustment[]>([]);
  readonly adjustments = this.#adjustments.asReadonly();

  getAdjustments(): Observable<StockAdjustment[]> {
    return simulateRequest(this.#adjustments());
  }

  createAdjustment(productId: string, newStock: number, reason: string): Observable<StockAdjustment> {
    const product = this.products.getProduct(productId);
    if (!product) return throwError(() => new Error('Producto no encontrado.'));

    const previousStock = product.currentStock;
    const delta = Math.round((newStock - previousStock) * 1000) / 1000;
    const user = this.auth.currentUser();
    const userName = user?.fullName ?? 'Usuario';

    this.products.applyStockChange({
      productId,
      delta,
      type: 'ajuste',
      reference: `Ajuste manual: ${reason}`,
      createdBy: userName,
    });

    const adjustment: StockAdjustment = {
      id: generateId(),
      productId,
      productName: product.name,
      previousStock,
      newStock,
      quantityDelta: delta,
      reason,
      date: new Date().toISOString(),
      createdBy: userName,
    };
    this.#adjustments.update((list) => [adjustment, ...list]);

    this.audit.log({
      userId: user?.id ?? '',
      userName,
      module: 'inventario',
      action: 'Ajustó inventario',
      description: `${userName} ajustó el stock de ${product.name} de ${previousStock} a ${newStock} ${product.unit}.`,
    });

    return simulateRequest(adjustment);
  }
}
