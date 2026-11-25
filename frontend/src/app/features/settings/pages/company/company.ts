import { Component, computed, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { TenantService } from '../../../../core/services/tenant.service';
import { ToastService } from '../../../../core/services/toast.service';
import { AuthService } from '../../../../core/services/auth.service';
import { BillingEnvironment } from '../../../../core/models/tenant.model';
import { PageHeader } from '../../../../shared/components/page-header/page-header';
import { Button } from '../../../../shared/components/button/button';
import { Card } from '../../../../shared/components/card/card';
import { FormField } from '../../../../shared/components/form-field/form-field';
import { Icon } from '../../../../shared/components/icon/icon';

@Component({
  selector: 'app-company',
  imports: [ReactiveFormsModule, PageHeader, Button, Card, FormField, Icon],
  templateUrl: './company.html',
  styleUrl: './company.scss',
})
export class Company {
  private tenantService = inject(TenantService);
  private toast = inject(ToastService);
  private auth = inject(AuthService);
  private fb = inject(FormBuilder);

  tenant = this.tenantService.tenant;
  loading = signal(true);
  savingGeneral = signal(false);
  savingBilling = signal(false);
  uploading = signal(false);

  /** Solo el Administrador modifica la empresa; el backend responde 403 a los demás. */
  isAdmin = computed(() => this.auth.currentUser()?.role === 'admin');

  certificateFile = signal<File | null>(null);
  certificatePassword = signal('');

  form = this.fb.nonNullable.group({
    businessName: ['', Validators.required],
    tradeName: [''],
    economicActivity: [''],
    address: [''],
    email: ['', [Validators.required, Validators.email]],
  });

  billingForm = this.fb.nonNullable.group({
    environment: ['pruebas' as BillingEnvironment, Validators.required],
    establishment: ['001', [Validators.required, Validators.pattern(/^\d{3}$/)]],
    emissionPoint: ['001', [Validators.required, Validators.pattern(/^\d{3}$/)]],
    requiredToKeepAccounts: [false],
    rimpe: [false],
    specialTaxpayer: ['', Validators.pattern(/^\d{1,13}$/)],
  });

  constructor() {
    this.tenantService.getTenant().subscribe({
      next: (tenant) => {
        this.form.patchValue({
          businessName: tenant.businessName,
          tradeName: tenant.tradeName ?? '',
          economicActivity: tenant.economicActivity ?? '',
          address: tenant.address ?? '',
          email: tenant.email,
        });
        if (tenant.billing) {
          this.billingForm.patchValue({
            ...tenant.billing,
            specialTaxpayer: tenant.billing.specialTaxpayer ?? '',
          });
        }
        this.loading.set(false);
      },
      error: () => this.loading.set(false),
    });
  }

  save(): void {
    if (this.form.invalid || this.savingGeneral()) {
      this.form.markAllAsTouched();
      return;
    }
    const raw = this.form.getRawValue();
    this.savingGeneral.set(true);
    this.tenantService
      .updateTenant({
        businessName: raw.businessName.trim(),
        tradeName: raw.tradeName.trim() || null,
        economicActivity: raw.economicActivity.trim() || null,
        address: raw.address.trim() || null,
        email: raw.email.trim(),
      })
      .subscribe({
        next: () => {
          this.toast.success('Datos de la empresa actualizados.');
          this.savingGeneral.set(false);
        },
        // El interceptor ya mostró el motivo del error.
        error: () => this.savingGeneral.set(false),
      });
  }

  saveBilling(): void {
    if (this.billingForm.invalid || this.savingBilling()) {
      this.billingForm.markAllAsTouched();
      return;
    }
    const raw = this.billingForm.getRawValue();
    this.savingBilling.set(true);
    this.tenantService
      .saveBillingSettings({ ...raw, specialTaxpayer: raw.specialTaxpayer.trim() || null })
      .subscribe({
        next: () => {
          this.toast.success('Configuración de facturación guardada.');
          this.savingBilling.set(false);
        },
        error: () => this.savingBilling.set(false),
      });
  }

  onCertificateSelected(event: Event): void {
    const input = event.target as HTMLInputElement;
    this.certificateFile.set(input.files?.[0] ?? null);
  }

  uploadCertificate(): void {
    const file = this.certificateFile();
    const password = this.certificatePassword();
    if (!file || !password || this.uploading()) return;

    this.uploading.set(true);
    this.tenantService.uploadCertificate(file, password).subscribe({
      next: () => {
        this.toast.success('Firma electrónica guardada.');
        this.certificateFile.set(null);
        this.certificatePassword.set('');
        this.uploading.set(false);
        // Vuelve a pedir la empresa para ver el nuevo estado y vencimiento de la firma.
        this.tenantService.getTenant().subscribe();
      },
      error: () => this.uploading.set(false),
    });
  }
}
