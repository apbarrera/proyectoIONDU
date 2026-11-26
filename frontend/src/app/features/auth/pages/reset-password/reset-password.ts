import { Component, computed, inject, signal } from '@angular/core';
import { toSignal } from '@angular/core/rxjs-interop';
import { AbstractControl, FormBuilder, ReactiveFormsModule, ValidationErrors, Validators } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { map } from 'rxjs';
import { PasswordResetService } from '../../services/password-reset.service';
import { ToastService } from '../../../../core/services/toast.service';
import { Button } from '../../../../shared/components/button/button';
import { FormField } from '../../../../shared/components/form-field/form-field';
import { Logo } from '../../../../shared/components/logo/logo';
import { apiErrorMessage } from '../../../../core/utils/api-error.util';

/** Mismo mínimo que el backend (app/core/contrasenas.py). */
export const MIN_PASSWORD_LENGTH = 10;

function samePasswords(group: AbstractControl): ValidationErrors | null {
  return group.get('password')?.value === group.get('confirm')?.value ? null : { mismatch: true };
}

/** Página del enlace del correo: recuperación o invitación. Funciona con o sin sesión. */
@Component({
  selector: 'app-reset-password',
  imports: [ReactiveFormsModule, RouterLink, Button, FormField, Logo],
  templateUrl: './reset-password.html',
  styleUrl: '../login/login.scss',
})
export class ResetPassword {
  private readonly fb = inject(FormBuilder);
  private readonly resets = inject(PasswordResetService);
  private readonly router = inject(Router);
  private readonly toast = inject(ToastService);

  readonly minLength = MIN_PASSWORD_LENGTH;
  token = toSignal(inject(ActivatedRoute).queryParamMap.pipe(map((params) => params.get('token') ?? '')), {
    initialValue: '',
  });
  hasToken = computed(() => this.token().length >= 20);

  submitting = signal(false);
  errorMessage = signal<string | null>(null);

  form = this.fb.nonNullable.group(
    {
      password: ['', [Validators.required, Validators.minLength(MIN_PASSWORD_LENGTH)]],
      confirm: ['', Validators.required],
    },
    { validators: samePasswords },
  );

  submit(): void {
    if (this.form.invalid || this.submitting() || !this.hasToken()) {
      this.form.markAllAsTouched();
      return;
    }
    this.submitting.set(true);
    this.errorMessage.set(null);
    this.resets.confirm(this.token(), this.form.getRawValue().password).subscribe({
      next: () => {
        this.toast.success('Listo. Ya puedes iniciar sesión con tu nueva contraseña.');
        this.router.navigateByUrl('/login');
      },
      error: (error: unknown) => {
        this.errorMessage.set(apiErrorMessage(error));
        this.submitting.set(false);
      },
    });
  }
}
