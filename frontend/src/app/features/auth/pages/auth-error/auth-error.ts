import { Component, inject, signal } from '@angular/core';
import { Router } from '@angular/router';
import { AuthService } from '../../../../core/services/auth.service';
import { Button } from '../../../../shared/components/button/button';
import { Icon } from '../../../../shared/components/icon/icon';
import { Logo } from '../../../../shared/components/logo/logo';

@Component({
  selector: 'app-auth-error',
  imports: [Button, Icon, Logo],
  templateUrl: './auth-error.html',
  styleUrl: './auth-error.scss',
})
export class AuthError {
  private readonly auth = inject(AuthService);
  private readonly router = inject(Router);

  readonly retrying = signal(false);
  readonly errorMessage = signal<string | null>(null);

  async retry(): Promise<void> {
    if (this.retrying()) return;

    this.retrying.set(true);
    this.errorMessage.set(null);

    try {
      await this.auth.initialize();

      switch (this.auth.status()) {
        case 'authenticated':
          await this.router.navigateByUrl(this.auth.defaultRouteForCurrentUser());
          break;
        case 'company-selection-required':
          await this.router.navigateByUrl('/select-company');
          break;
        case 'no-company':
          await this.router.navigateByUrl('/no-company');
          break;
        case 'unauthenticated':
          await this.router.navigateByUrl('/login');
          break;
        default:
          throw new Error('No se pudo recuperar el contexto de tu cuenta.');
      }
    } catch {
      this.errorMessage.set(
        'No pudimos conectar con el servicio. Comprueba tu conexión e inténtalo nuevamente.',
      );
    } finally {
      this.retrying.set(false);
    }
  }

  async logout(): Promise<void> {
    try {
      await this.auth.logout();
    } finally {
      await this.router.navigateByUrl('/login');
    }
  }
}
