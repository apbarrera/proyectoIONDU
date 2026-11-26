import { Component, inject, signal } from '@angular/core';
import {
  AbstractControl,
  FormBuilder,
  ReactiveFormsModule,
  ValidationErrors,
  Validators,
} from '@angular/forms';
import { ThemeService, ThemePreference } from '../../../../core/services/theme.service';
import { AuthService } from '../../../../core/services/auth.service';
import { ToastService } from '../../../../core/services/toast.service';
import { PageHeader } from '../../../../shared/components/page-header/page-header';
import { Card } from '../../../../shared/components/card/card';
import { Button } from '../../../../shared/components/button/button';
import { FormField } from '../../../../shared/components/form-field/form-field';
import { IconName } from '../../../../shared/icons/icons.generated';
import { Icon } from '../../../../shared/components/icon/icon';

const OPTIONS: { value: ThemePreference; label: string; icon: IconName }[] = [
  { value: 'light', label: 'Claro', icon: 'sun' },
  { value: 'dark', label: 'Oscuro', icon: 'moon' },
  { value: 'system', label: 'Sistema', icon: 'system' },
];

/** Mismo mínimo que el backend (app/core/contrasenas.py). */
export const PASSWORD_MIN_LENGTH = 10;

function passwordsMatch(group: AbstractControl): ValidationErrors | null {
  const { newPassword, confirmPassword } = group.value as Record<string, string>;
  return confirmPassword && newPassword !== confirmPassword ? { mismatch: true } : null;
}

@Component({
  selector: 'app-preferences',
  imports: [ReactiveFormsModule, PageHeader, Card, Icon, Button, FormField],
  templateUrl: './preferences.html',
  styleUrl: './preferences.scss',
})
export class Preferences {
  themeService = inject(ThemeService);
  private auth = inject(AuthService);
  private toast = inject(ToastService);
  private fb = inject(FormBuilder);

  options = OPTIONS;
  minLength = PASSWORD_MIN_LENGTH;
  changingPassword = signal(false);

  passwordForm = this.fb.nonNullable.group(
    {
      currentPassword: ['', Validators.required],
      newPassword: ['', [Validators.required, Validators.minLength(PASSWORD_MIN_LENGTH)]],
      confirmPassword: ['', Validators.required],
    },
    { validators: passwordsMatch },
  );

  fieldError(name: 'currentPassword' | 'newPassword' | 'confirmPassword'): string | null {
    const control = this.passwordForm.controls[name];
    if (!control.touched) return null;
    if (control.hasError('required')) return 'Este campo es obligatorio.';
    if (control.hasError('minlength')) return `Debe tener al menos ${PASSWORD_MIN_LENGTH} caracteres.`;
    if (name === 'confirmPassword' && this.passwordForm.hasError('mismatch')) {
      return 'Las contraseñas no coinciden.';
    }
    return null;
  }

  async changePassword(): Promise<void> {
    if (this.passwordForm.invalid) {
      this.passwordForm.markAllAsTouched();
      return;
    }
    const { currentPassword, newPassword } = this.passwordForm.getRawValue();
    this.changingPassword.set(true);
    try {
      await this.auth.changePassword(currentPassword, newPassword);
      this.passwordForm.reset();
      this.toast.success('Contraseña actualizada. Se cerraron tus sesiones en otros dispositivos.');
    } catch {
      // El interceptor de errores ya mostró el mensaje del servidor.
    } finally {
      this.changingPassword.set(false);
    }
  }
}
