import { Component, inject } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { TenantService } from '../../../../core/services/tenant.service';
import { ToastService } from '../../../../core/services/toast.service';
import { AuditService } from '../../../../core/services/audit.service';
import { AuthService } from '../../../../core/services/auth.service';
import { PageHeader } from '../../../../shared/components/page-header/page-header';
import { Button } from '../../../../shared/components/button/button';
import { Card } from '../../../../shared/components/card/card';
import { FormField } from '../../../../shared/components/form-field/form-field';

@Component({
  selector: 'app-company',
  imports: [ReactiveFormsModule, PageHeader, Button, Card, FormField],
  templateUrl: './company.html',
  styleUrl: './company.scss',
})
export class Company {
  private tenantService = inject(TenantService);
  private toast = inject(ToastService);
  private audit = inject(AuditService);
  private auth = inject(AuthService);
  private fb = inject(FormBuilder);

  tenant = this.tenantService.tenant;

  form = this.fb.nonNullable.group({
    businessName: [this.tenant().businessName, Validators.required],
    tradeName: [this.tenant().tradeName, Validators.required],
    ruc: [this.tenant().ruc, [Validators.required, Validators.pattern(/^\d{13}$/)]],
    economicActivity: [this.tenant().economicActivity],
    address: [this.tenant().address],
    phone: [this.tenant().phone],
    email: [this.tenant().email, Validators.email],
  });

  save(): void {
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }
    this.tenantService.updateTenant(this.form.getRawValue()).subscribe(() => {
      this.toast.success('Datos de la empresa actualizados.');
      const user = this.auth.currentUser();
      this.audit.log({
        userId: user?.id ?? '',
        userName: user?.fullName ?? 'Usuario',
        module: 'configuracion',
        action: 'Actualizó configuración',
        description: `${user?.fullName} modificó la configuración de la empresa.`,
      });
    });
  }
}
