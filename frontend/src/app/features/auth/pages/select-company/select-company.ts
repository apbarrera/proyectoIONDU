import { Component, inject, signal } from '@angular/core';
import { Router } from '@angular/router';
import { AuthService } from '../../../../core/services/auth.service';
import { CompanyContextService } from '../../../../core/services/company-context.service';
import { Button } from '../../../../shared/components/button/button';
import { Icon } from '../../../../shared/components/icon/icon';
import { Logo } from '../../../../shared/components/logo/logo';

@Component({
  selector: 'app-select-company',
  imports: [Button, Icon, Logo],
  templateUrl: './select-company.html',
  styleUrl: './select-company.scss',
})
export class SelectCompany {
  private readonly auth = inject(AuthService);
  private readonly router = inject(Router);
  private readonly companyContext = inject(CompanyContextService);

  readonly companies = this.companyContext.companies;
  readonly selectingCompanyId = signal<number | null>(null);
  readonly errorMessage = signal<string | null>(null);

  async selectCompany(companyId: number): Promise<void> {
    if (this.selectingCompanyId() !== null) return;

    this.selectingCompanyId.set(companyId);
    this.errorMessage.set(null);

    try {
      await this.auth.selectCompany(companyId);

      if (this.auth.status() !== 'authenticated') {
        throw new Error('No se pudo completar la selección de empresa.');
      }

      await this.router.navigateByUrl(this.auth.defaultRouteForCurrentUser());
    } catch (error) {
      this.errorMessage.set(
        error instanceof Error
          ? error.message
          : 'No se pudo seleccionar la empresa. Inténtalo nuevamente.',
      );
    } finally {
      this.selectingCompanyId.set(null);
    }
  }

  async logout(): Promise<void> {
    await this.auth.logout();
    await this.router.navigateByUrl('/login');
  }
}
