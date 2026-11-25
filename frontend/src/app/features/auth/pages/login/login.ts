import { Component, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { Router } from '@angular/router';
import { AuthService } from '../../../../core/services/auth.service';
import { ToastService } from '../../../../core/services/toast.service';
import { Button } from '../../../../shared/components/button/button';
import { FormField } from '../../../../shared/components/form-field/form-field';
import { Logo } from '../../../../shared/components/logo/logo';

@Component({
  selector: 'app-login',
  imports: [ReactiveFormsModule, Button, FormField, Logo],
  templateUrl: './login.html',
  styleUrl: './login.scss',
})
export class Login {
  private readonly fb = inject(FormBuilder);
  private readonly auth = inject(AuthService);
  private readonly router = inject(Router);
  private readonly toast = inject(ToastService);

  submitting = signal(false);
  errorMessage = signal<string | null>(null);

  form = this.fb.nonNullable.group({
    email: ['', [Validators.required, Validators.email]],
    password: ['', [Validators.required]],
  });

  async submit(): Promise<void> {
    if (this.form.invalid || this.submitting()) {
      this.form.markAllAsTouched();
      return;
    }

    this.submitting.set(true);
    this.errorMessage.set(null);

    const { email, password } = this.form.getRawValue();

    try {
      await this.auth.login({ email, password });

      switch (this.auth.status()) {
        case 'authenticated':
          this.toast.success('¡Bienvenido de nuevo!');
          await this.router.navigateByUrl(this.auth.defaultRouteForCurrentUser());
          break;

        case 'no-company':
          await this.router.navigateByUrl('/no-company');
          break;

        case 'company-selection-required':
          await this.router.navigateByUrl('/select-company');
          break;

        default:
          throw new Error('No se pudo completar la configuración de tu sesión.');
      }
    } catch (error) {
      this.errorMessage.set(
        error instanceof Error
          ? error.message
          : 'No se pudo iniciar sesión. Inténtalo nuevamente.',
      );
    } finally {
      this.submitting.set(false);
    }
  }
}
