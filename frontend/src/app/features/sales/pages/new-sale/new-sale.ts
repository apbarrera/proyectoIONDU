import { Component, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { SalesService } from '../../services/sales.service';
import { ProductsService } from '../../../inventory/services/products.service';
import { TenantService } from '../../../../core/services/tenant.service';
import { ToastService } from '../../../../core/services/toast.service';
import { PaymentMethod } from '../../models/sale.model';
import { PageHeader } from '../../../../shared/components/page-header/page-header';
import { Button } from '../../../../shared/components/button/button';
import { Card } from '../../../../shared/components/card/card';
import { EmptyState } from '../../../../shared/components/empty-state/empty-state';
import { Icon } from '../../../../shared/components/icon/icon';

interface CartLine {
  productId: string;
  productName: string;
  unitPrice: number;
  quantity: number;
  availableStock: number;
}

@Component({
  selector: 'app-new-sale',
  imports: [FormsModule, PageHeader, Button, Card, EmptyState, Icon],
  templateUrl: './new-sale.html',
  styleUrl: './new-sale.scss',
})
export class NewSale {
  productsService = inject(ProductsService);
  private salesService = inject(SalesService);
  private tenant = inject(TenantService);
  private toast = inject(ToastService);
  private router = inject(Router);

  sellableProducts = computed(() => this.productsService.products().filter((p) => p.salePrice != null && p.active));

  selectedProductId = signal('');
  customerName = signal('');
  paymentMethod = signal<PaymentMethod>('efectivo');
  observation = signal('');
  submitting = signal(false);

  cart = signal<CartLine[]>([]);

  ivaRate = this.tenant.tenant().ivaRate;

  subtotal = computed(() => Math.round(this.cart().reduce((sum, l) => sum + l.unitPrice * l.quantity, 0) * 100) / 100);
  ivaAmount = computed(() => Math.round(this.subtotal() * this.ivaRate * 100) / 100);
  total = computed(() => Math.round((this.subtotal() + this.ivaAmount()) * 100) / 100);

  addToCart(): void {
    const product = this.productsService.getProduct(this.selectedProductId());
    if (!product || product.salePrice == null) return;

    this.cart.update((lines) => {
      const existing = lines.find((l) => l.productId === product.id);
      if (existing) {
        return lines.map((l) => (l.productId === product.id ? { ...l, quantity: l.quantity + 1 } : l));
      }
      return [
        ...lines,
        {
          productId: product.id,
          productName: product.name,
          unitPrice: product.salePrice!,
          quantity: 1,
          availableStock: product.currentStock,
        },
      ];
    });
    this.selectedProductId.set('');
  }

  updateQuantity(productId: string, quantity: number): void {
    if (quantity < 1) return;
    this.cart.update((lines) => lines.map((l) => (l.productId === productId ? { ...l, quantity } : l)));
  }

  removeFromCart(productId: string): void {
    this.cart.update((lines) => lines.filter((l) => l.productId !== productId));
  }

  confirmSale(): void {
    if (this.cart().length === 0 || this.submitting()) return;
    this.submitting.set(true);

    this.salesService
      .createSale({
        customerName: this.customerName(),
        items: this.cart().map((l) => ({ productId: l.productId, quantity: l.quantity })),
        paymentMethod: this.paymentMethod(),
        observation: this.observation() || undefined,
      })
      .subscribe({
        next: (sale) => {
          this.toast.success(`Venta #${sale.folio} registrada por $${sale.total.toFixed(2)}.`);
          this.cart.set([]);
          this.customerName.set('');
          this.observation.set('');
          this.submitting.set(false);
          this.router.navigateByUrl('/sales/history');
        },
        error: (err: Error) => {
          this.toast.error(err.message);
          this.submitting.set(false);
        },
      });
  }
}
