import { Component, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { Observable, of, switchMap } from 'rxjs';
import { SalesService } from '../../services/sales.service';
import { CustomersApiService, FINAL_CONSUMER_ID } from '../../services/customers-api.service';
import { Customer } from '../../models/customer.model';
import { BillingService } from '../../../billing/services/billing.service';
import { ProductsApiService } from '../../../inventory/services/products-api.service';
import { Product } from '../../../inventory/models/product.model';
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

const ID_PATTERN = /^\d{10}(\d{3})?$/;
const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

@Component({
  selector: 'app-new-sale',
  imports: [FormsModule, PageHeader, Button, Card, EmptyState, Icon, Switch],
  templateUrl: './new-sale.html',
  styleUrl: './new-sale.scss',
})
export class NewSale {
  private productsApi = inject(ProductsApiService);
  private customersApi = inject(CustomersApiService);
  private salesService = inject(SalesService);
  private billingService = inject(BillingService);
  private tenant = inject(TenantService);
  private toast = inject(ToastService);
  private router = inject(Router);

  products = signal<Product[]>([]);
  productsLoading = signal(true);

  sellableProducts = computed(() => this.products().filter((p) => p.salePrice != null && p.active));

  selectedProductId = signal('');
  customerName = signal('');
  paymentMethod = signal<PaymentMethod>('efectivo');
  observation = signal('');
  submitting = signal(false);

  /** Cada venta nueva se factura electrónicamente salvo que el usuario lo desactive. */
  emitInvoice = signal(true);
  rucOrCedula = signal(FINAL_CONSUMER_ID);
  email = signal('');

  /** Cliente ya registrado para la identificación escrita (autocompleta nombre y correo). */
  foundCustomer = signal<Customer | null>(null);

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

  /** Con factura y un cliente que todavía no existe, hace falta su nombre para registrarlo. */
  nameError = computed(() => {
    if (!this.#needsCustomer() || this.foundCustomer() || this.customerName().trim()) return '';
    return 'Escribe el nombre del cliente para registrarlo.';
  });

  canConfirm = computed(
    () => this.cart().length > 0 && !this.idError() && !this.emailError() && !this.nameError(),
  );

  constructor() {
    this.productsApi.getProducts().subscribe({
      next: (products) => {
        this.products.set(products);
        this.productsLoading.set(false);
      },
      error: () => this.productsLoading.set(false),
    });
  }

  /** Al escribir una cédula o RUC completo, busca si el cliente ya existe y lo autocompleta. */
  onIdentificationChange(value: string): void {
    this.rucOrCedula.set(value);
    this.foundCustomer.set(null);

    const id = value.trim();
    if (!ID_PATTERN.test(id) || id === FINAL_CONSUMER_ID) return;

    this.customersApi.lookup(id).subscribe({
      // Ignora la respuesta si el usuario ya cambió el número mientras llegaba.
      next: (customer) => {
        if (customer && this.rucOrCedula().trim() === id) {
          this.foundCustomer.set(customer);
          this.customerName.set(customer.name);
          if (customer.email && !this.email()) this.email.set(customer.email);
        }
      },
      error: () => undefined,
    });
  }

  addToCart(): void {
    const product = this.products().find((p) => p.id === this.selectedProductId());
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

    const invoice = this.emitInvoice();
    const email = this.email().trim();

    this.#resolveCustomer(email)
      .pipe(
        switchMap((customer) =>
          this.salesService.createSale({
            customerId: customer?.id ?? null,
            items: this.cart().map((l) => ({ productId: Number(l.productId), quantity: l.quantity })),
            paymentMethod: this.paymentMethod(),
            observation: this.observation() || undefined,
          }),
        ),
      )
      .subscribe({
        next: (sale) => {
          this.toast.success(`Venta #${sale.folio} registrada por $${sale.total.toFixed(2)}.`);
          this.submitting.set(false);
          this.router.navigateByUrl('/sales/history');

          // La factura se emite en segundo plano: el historial muestra su estado.
          if (invoice) {
            this.billingService.invoiceSale(sale, email).subscribe({
              next: (result) =>
                result.status === 'autorizada'
                  ? this.toast.success(`Factura ${result.numero} autorizada.`)
                  : result.status === 'rechazada'
                    ? this.toast.error(`Factura ${result.numero} rechazada: ${result.rejectionReason}`)
                    : this.toast.info(`Factura ${result.numero} enviada al SRI; queda pendiente de autorización.`),
              // El interceptor ya mostró el motivo del error.
              error: () => undefined,
            });
          }
        },
        // El interceptor ya mostró el mensaje del backend.
        error: () => this.submitting.set(false),
      });
  }

  #needsCustomer(): boolean {
    const id = this.rucOrCedula().trim();
    return this.emitInvoice() && ID_PATTERN.test(id) && id !== FINAL_CONSUMER_ID;
  }

  /** Cliente de la venta: el registrado, uno nuevo, o `null` para consumidor final. */
  #resolveCustomer(email: string): Observable<Customer | null> {
    if (!this.#needsCustomer()) return of(null);
    const found = this.foundCustomer();
    if (found) return of(found);

    return this.customersApi.findOrCreate({
      identification: this.rucOrCedula().trim(),
      name: this.customerName().trim(),
      email: email || null,
    });
  }
}
