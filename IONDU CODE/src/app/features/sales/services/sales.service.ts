import { Injectable, computed, inject, signal } from '@angular/core';
import { Observable, throwError } from 'rxjs';
import { PaymentMethod, Sale, SaleLineItem } from '../models/sale.model';
import { SALES_MOCK } from '../../../mocks/sales.mock';
import { simulateRequest } from '../../../core/services/mock-http.util';
import { generateId } from '../../../core/utils/id.util';
import { ProductsService } from '../../inventory/services/products.service';
import { AuditService } from '../../../core/services/audit.service';
import { AuthService } from '../../../core/services/auth.service';
import { TenantService } from '../../../core/services/tenant.service';

export interface NewSaleInput {
  customerName: string;
  items: { productId: string; quantity: number }[];
  paymentMethod: PaymentMethod;
  observation?: string;
}

@Injectable({ providedIn: 'root' })
export class SalesService {
  private products = inject(ProductsService);
  private audit = inject(AuditService);
  private auth = inject(AuthService);
  private tenant = inject(TenantService);

  #sales = signal<Sale[]>(SALES_MOCK);
  readonly sales = this.#sales.asReadonly();

  readonly totalRevenue = computed(() =>
    this.#sales()
      .filter((s) => s.status === 'completada')
      .reduce((sum, s) => sum + s.total, 0),
  );

  getSales(): Observable<Sale[]> {
    return simulateRequest(this.#sales());
  }

  /**
   * Orchestrates the full sale side-effect chain: decrement stock per line item,
   * write the sale, then log the audit entry — mirrors the DAG every other
   * mutating service in the app follows (domain service → movements → audit).
   */
  createSale(input: NewSaleInput): Observable<Sale> {
    if (input.items.length === 0) {
      return throwError(() => new Error('Agrega al menos un producto a la venta.'));
    }

    const shortage = input.items.find((item) => {
      const product = this.products.getProduct(item.productId);
      return !product || product.currentStock < item.quantity;
    });
    if (shortage) {
      const product = this.products.getProduct(shortage.productId);
      return throwError(() => new Error(`Stock insuficiente de ${product?.name ?? 'producto'}.`));
    }

    const user = this.auth.currentUser();
    const userName = user?.fullName ?? 'Usuario';
    const ivaRate = this.tenant.tenant().ivaRate;

    const lineItems: SaleLineItem[] = input.items.map((item) => {
      const product = this.products.getProduct(item.productId)!;
      const unitPrice = product.salePrice ?? 0;
      return {
        productId: product.id,
        productName: product.name,
        quantity: item.quantity,
        unitPrice,
        subtotal: Math.round(unitPrice * item.quantity * 100) / 100,
      };
    });

    const subtotal = Math.round(lineItems.reduce((sum, i) => sum + i.subtotal, 0) * 100) / 100;
    const ivaAmount = Math.round(subtotal * ivaRate * 100) / 100;
    const total = Math.round((subtotal + ivaAmount) * 100) / 100;

    const sale: Sale = {
      id: generateId(),
      folio: this.#nextFolio(),
      date: new Date().toISOString(),
      customerName: input.customerName || 'Consumidor Final',
      items: lineItems,
      subtotal,
      ivaAmount,
      total,
      paymentMethod: input.paymentMethod,
      status: 'completada',
      observation: input.observation,
      createdBy: userName,
    };

    lineItems.forEach((item) => {
      this.products.applyStockChange({
        productId: item.productId,
        delta: -item.quantity,
        type: 'venta',
        reference: `Venta #${sale.folio}`,
        createdBy: userName,
      });
    });

    this.#sales.update((list) => [sale, ...list]);

    this.audit.log({
      userId: user?.id ?? '',
      userName,
      module: 'ventas',
      action: 'Registró venta',
      description: `${userName} registró la venta #${sale.folio} por $${total.toFixed(2)}.`,
    });

    return simulateRequest(sale);
  }

  #nextFolio(): string {
    const max = this.#sales().reduce((m, s) => Math.max(m, Number(s.folio)), 100);
    return String(max + 1).padStart(6, '0');
  }
}
