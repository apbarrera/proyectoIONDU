import { ComponentFixture, TestBed } from '@angular/core/testing';
import { AuthService } from '../../../../core/services/auth.service';

import { Preferences } from './preferences';

describe('Preferences', () => {
  let component: Preferences;
  let fixture: ComponentFixture<Preferences>;
  let auth: { changePassword: ReturnType<typeof vi.fn> };

  beforeEach(async () => {
    auth = { changePassword: vi.fn().mockResolvedValue(undefined) };
    await TestBed.configureTestingModule({
      imports: [Preferences],
      providers: [{ provide: AuthService, useValue: auth }],
    }).compileComponents();

    fixture = TestBed.createComponent(Preferences);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('no envía la contraseña si la confirmación no coincide', async () => {
    component.passwordForm.setValue({
      currentPassword: 'Actual-12345',
      newPassword: 'Nueva-123456',
      confirmPassword: 'Distinta-123456',
    });
    component.passwordForm.markAllAsTouched();

    await component.changePassword();

    expect(auth.changePassword).not.toHaveBeenCalled();
    expect(component.fieldError('confirmPassword')).toBe('Las contraseñas no coinciden.');
  });

  it('exige el mínimo de caracteres del backend', () => {
    component.passwordForm.controls.newPassword.setValue('corta');
    component.passwordForm.controls.newPassword.markAsTouched();
    expect(component.fieldError('newPassword')).toContain('10 caracteres');
  });

  it('cambia la contraseña y limpia el formulario', async () => {
    component.passwordForm.setValue({
      currentPassword: 'Actual-12345',
      newPassword: 'Nueva-123456',
      confirmPassword: 'Nueva-123456',
    });

    await component.changePassword();

    expect(auth.changePassword).toHaveBeenCalledWith('Actual-12345', 'Nueva-123456');
    expect(component.passwordForm.getRawValue().newPassword).toBe('');
  });
});
