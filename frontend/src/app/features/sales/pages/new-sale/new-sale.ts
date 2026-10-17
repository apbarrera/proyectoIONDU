import { Component, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { SalesService } from '../../services/sales.service';
import { BillingService } from '../../../billing/services/billing.service';
import { ProductsService } from '../../../inventory/services/products.service';
import { TenantService } from '../../../../core/services/tenant.service';
import { ToastService } from '../../../../core/services/toast.service';
import { PaymentMethod } from '../../models/sale.model';
import { PageHeader } from '../../../../shared/components/page-header/page-header';
import { Button } from '../../../../shared/components/button/button';
import { Card } from '../../../../shared/components/card/card';
import { EmptyState } from '../../../../shared/components/empty-state/empty-state';
import { Icon } from '../../../../shared/components/icon/icon';
import { Switch } from '../../../../shared/components/switch/switch';

interface CartLine {
  productId: string;
  productName: string;
  unitPrice: number;
  quantity: number;
  availableStock: number;
}

const FINAL_CONSUMER_ID = '9999999999';
const ID_PATTERN = /^\d{10}(\d{3})?$/;
const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

@Component({
  selector: 'app-new-sale',
  imports: [FormsModule, PageHeader, Button, Card, EmptyState, Icon, Switch],
  templateUrl: './new-sale.html',
  styleUrl: './new-sale.scss',
})
export class NewSale {
  productsService = inject(ProductsService);
  private salesService = inject(SalesService);
  private billingService = inject(BillingService);
  private tenant = inject(TenantService);
  private toast = inject(ToastService);
  private router = inject(Router);

  sellableProducts = computed(() => this.productsService.products().filter((p) => p.salePrice != null && p.active));

  selectedProductId = signal('');
  customerName = signal('');
  paymentMethod = signal<PaymentMethod>('efectivo');
  observation = signal('');
  submitting = signal(false);

  /** Cada venta nueva se factura electrónicamente salvo que el usuario lo desactive. */
  emitInvoice = signal(true);
  rucOrCedula = signal(FINAL_CONSUMER_ID);
  email = signal('');

  cart = signal<CartLine[]>([]);

  ivaRate = this.tenant.tenant().ivaRate;

  subtotal = computed(() => Math.round(this.cart().reduce((sum, l) => sum + l.unitPrice * l.quantity, 0) * 100) / 100);
  ivaAmount = computed(() => Math.round(this.subtotal() * this.ivaRate * 100) / 100);
  total = computed(() => Math.round((this.subtotal() + this.ivaAmount()) * 100) / 100);

  idError = computed(() => {
    if (!this.emitInvoice()) return '';
    return ID_PATTERN.test(this.rucOrCedula().trim()) ? '' : 'Ingresa una cédula (10 dígitos) o un RUC (13 dígitos).';
  });

  emailError = computed(() => {
    const value = this.email().trim();
    if (!this.emitInvoice() || !value) return '';
    return EMAIL_PATTERN.test(value) ? '' : 'El correo no es válido.';
  });

  canConfirm = computed(() => this.cart().length > 0 && !this.idError() && !this.emailError());

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
    if (!this.canConfirm() || this.submitting()) return;
    this.submitting.set(true);

    const customer = {
      rucOrCedula: this.rucOrCedula().trim(),
      razonSocial: this.customerName().trim() || 'Consumidor Final',
      email: this.email().trim(),
    };
    const invoice = this.emitInvoice();

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
          this.submitting.set(false);
          this.router.navigateByUrl('/sales/history');

          // La factura se emite en segundo plano: el historial muestra su estado en vivo.
          if (invoice) {
            this.billingService.invoiceSale(sale, customer).subscribe({
              next: (result) =>
                result.status === 'autorizada'
                  ? this.toast.success(`Factura ${result.numero} autorizada.`)
                  : this.toast.error(`Factura ${result.numero} rechazada. Puedes reintentarla desde el historial.`),
              error: () => this.toast.error('No se pudo emitir la factura. Puedes reintentarla desde el historial.'),
            });
          }
        },
        error: (err: Error) => {
          this.toast.error(err.message);
          this.submitting.set(false);
        },
      });
  }
}
