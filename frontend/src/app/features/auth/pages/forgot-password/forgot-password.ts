import { Component, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { PasswordResetService } from '../../services/password-reset.service';
import { Button } from '../../../../shared/components/button/button';
import { FormField } from '../../../../shared/components/form-field/form-field';
import { Logo } from '../../../../shared/components/logo/logo';
import { apiErrorMessage } from '../../../../core/utils/api-error.util';

@Component({
  selector: 'app-forgot-password',
  imports: [ReactiveFormsModule, RouterLink, Button, FormField, Logo],
  templateUrl: './forgot-password.html',
  styleUrl: '../login/login.scss',
})
export class ForgotPassword {
  private readonly fb = inject(FormBuilder);
  private readonly resets = inject(PasswordResetService);

  submitting = signal(false);
  /** Mensaje del backend tras enviar (igual exista o no la cuenta). */
  sentMessage = signal<string | null>(null);
  errorMessage = signal<string | null>(null);

  form = this.fb.nonNullable.group({ email: ['', [Validators.required, Validators.email]] });

  submit(): void {
    if (this.form.invalid || this.submitting()) {
      this.form.markAllAsTouched();
      return;
    }
    this.submitting.set(true);
    this.errorMessage.set(null);
    this.resets.request(this.form.getRawValue().email).subscribe({
      next: (message) => {
        this.sentMessage.set(message);
        this.submitting.set(false);
      },
      error: (error: unknown) => {
        this.errorMessage.set(apiErrorMessage(error));
        this.submitting.set(false);
      },
    });
  }
}
