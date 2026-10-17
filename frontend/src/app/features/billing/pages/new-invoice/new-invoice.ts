import { Component, computed, inject, signal } from '@angular/core';
import { FormBuilder, FormsModule, ReactiveFormsModule, Validators } from '@angular/forms';
import { Router } from '@angular/router';
import { BillingService } from '../../services/billing.service';
import { SalesService } from '../../../sales/services/sales.service';
import { ToastService } from '../../../../core/services/toast.service';
import { PageHeader } from '../../../../shared/components/page-header/page-header';
import { Button } from '../../../../shared/components/button/button';
import { Card } from '../../../../shared/components/card/card';
import { FormField } from '../../../../shared/components/form-field/form-field';

@Component({
  selector: 'app-new-invoice',
  imports: [ReactiveFormsModule, FormsModule, PageHeader, Button, Card, FormField],
  templateUrl: './new-invoice.html',
  styleUrl: './new-invoice.scss',
})
export class NewInvoice {
  salesService = inject(SalesService);
  private billingService = inject(BillingService);
  private toast = inject(ToastService);
  private router = inject(Router);
  private fb = inject(FormBuilder);

  selectedSaleId = signal('');
  submitting = signal(false);

  selectedSale = computed(() => this.salesService.sales().find((s) => s.id === this.selectedSaleId()));

  form = this.fb.nonNullable.group({
    rucOrCedula: ['9999999999', Validators.required],
    razonSocial: ['Consumidor Final', Validators.required],
    email: ['', Validators.email],
  });

  onSaleChange(saleId: string): void {
    this.selectedSaleId.set(saleId);
    const sale = this.salesService.sales().find((s) => s.id === saleId);
    if (sale && sale.customerName !== 'Consumidor Final') {
      this.form.patchValue({ razonSocial: sale.customerName });
    }
  }

  generateAndEmit(): void {
    const sale = this.selectedSale();
    if (!sale || this.form.invalid || this.submitting()) {
      this.form.markAllAsTouched();
      return;
    }

    this.submitting.set(true);
    const { rucOrCedula, razonSocial, email } = this.form.getRawValue();

    this.billingService
      .createDraft({
        saleId: sale.id,
        customer: { rucOrCedula, razonSocial, email },
        items: sale.items,
      })
      .subscribe((draft) => {
        this.toast.info(`Factura ${draft.numero} generada. Enviando al servicio de facturación…`);
        this.billingService.emit(draft.id).subscribe({
          next: (invoice) => {
            this.submitting.set(false);
            if (invoice.status === 'autorizada') {
              this.toast.success(`Factura ${invoice.numero} autorizada.`);
            } else {
              this.toast.error(`Factura ${invoice.numero} fue rechazada.`);
            }
            this.router.navigateByUrl('/billing/history');
          },
          error: () => this.submitting.set(false),
        });
      });
  }
}
