import { Component, inject } from '@angular/core';
import { Router } from '@angular/router';
import { AuthService } from '../../../../core/services/auth.service';
import { Button } from '../../../../shared/components/button/button';
import { Icon } from '../../../../shared/components/icon/icon';
import { Logo } from '../../../../shared/components/logo/logo';

@Component({
  selector: 'app-no-company',
  imports: [Button, Icon, Logo],
  templateUrl: './no-company.html',
  styleUrl: './no-company.scss',
})
export class NoCompany {
  private readonly auth = inject(AuthService);
  private readonly router = inject(Router);

  async logout(): Promise<void> {
    try {
      await this.auth.logout();
    } finally {
      await this.router.navigateByUrl('/login');
    }
  }
}
