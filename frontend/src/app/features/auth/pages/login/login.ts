import { Component, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { Router } from '@angular/router';
import { AuthService } from '../../../../core/services/auth.service';
import { ToastService } from '../../../../core/services/toast.service';
import { Button } from '../../../../shared/components/button/button';
import { FormField } from '../../../../shared/components/form-field/form-field';
import { Modal } from '../../../../shared/components/modal/modal';

@Component({
  selector: 'app-login',
  imports: [ReactiveFormsModule, Button, FormField, Modal],
  templateUrl: './login.html',
  styleUrl: './login.scss',
})
export class Login {
  private fb = inject(FormBuilder);
  private auth = inject(AuthService);
  private router = inject(Router);
  private toast = inject(ToastService);

  submitting = signal(false);
  errorMessage = signal<string | null>(null);

  recoveryOpen = signal(false);
  recoveryEmail = signal('');
  recoveryResult = signal<string | null>(null);

  form = this.fb.nonNullable.group({
    email: ['', [Validators.required, Validators.email]],
    password: ['', [Validators.required]],
    rememberSession: [true],
  });

  submit(): void {
    if (this.form.invalid || this.submitting()) {
      this.form.markAllAsTouched();
      return;
    }

    this.submitting.set(true);
    this.errorMessage.set(null);
    const { email, password, rememberSession } = this.form.getRawValue();

    this.auth.login({ email, password, rememberSession }).subscribe({
      next: () => {
        this.toast.success('¡Bienvenido de nuevo!');
        this.router.navigateByUrl(this.auth.defaultRouteForCurrentUser());
      },
      error: (err: Error) => {
        this.errorMessage.set(err.message);
        this.submitting.set(false);
      },
    });
  }

  openRecovery(): void {
    this.recoveryEmail.set(this.form.controls.email.value);
    this.recoveryResult.set(null);
    this.recoveryOpen.set(true);
  }

  submitRecovery(): void {
    const email = this.recoveryEmail().trim().toLowerCase();
    if (email === 'admin@iondu.demo') {
      this.recoveryResult.set('Hemos enviado un enlace de recuperación a tu correo.');
    } else {
      this.recoveryResult.set('Contacta a tu administrador para restablecer tu contraseña.');
    }
  }

  closeRecovery(): void {
    this.recoveryOpen.set(false);
  }
}
