import { signal, WritableSignal } from '@angular/core';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { Router } from '@angular/router';
import { AuthService, AuthStatus } from '../../../../core/services/auth.service';
import { ToastService } from '../../../../core/services/toast.service';
import { Login } from './login';

describe('Login', () => {
  let component: Login;
  let fixture: ComponentFixture<Login>;
  let authStatus: WritableSignal<AuthStatus>;
  let loginMock: ReturnType<typeof vi.fn>;
  let defaultRouteMock: ReturnType<typeof vi.fn>;
  let navigateByUrlMock: ReturnType<typeof vi.fn>;
  let successToastMock: ReturnType<typeof vi.fn>;

  beforeEach(async () => {
    authStatus = signal<AuthStatus>('authenticated');
    loginMock = vi.fn().mockResolvedValue(undefined);
    defaultRouteMock = vi.fn().mockReturnValue('/dashboard');
    navigateByUrlMock = vi.fn().mockResolvedValue(true);
    successToastMock = vi.fn();

    await TestBed.configureTestingModule({
      imports: [Login],
      providers: [
        {
          provide: AuthService,
          useValue: {
            login: loginMock,
            status: authStatus,
            defaultRouteForCurrentUser: defaultRouteMock,
          },
        },
        {
          provide: Router,
          useValue: { navigateByUrl: navigateByUrlMock },
        },
        {
          provide: ToastService,
          useValue: { success: successToastMock },
        },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(Login);
    component = fixture.componentInstance;
    fixture.detectChanges();
    await fixture.whenStable();
  });

  it('crea el componente', () => {
    expect(component).toBeTruthy();
  });

  it('no intenta iniciar sesión si el formulario es inválido', async () => {
    await component.submit();

    expect(loginMock).not.toHaveBeenCalled();
    expect(component.form.touched).toBe(true);
  });

  it('inicia sesión y redirige al dashboard cuando el usuario es administrador', async () => {
    component.form.setValue({
      email: 'admin@empresa.com',
      password: 'password-segura',
    });

    await component.submit();

    expect(loginMock).toHaveBeenCalledWith({
      email: 'admin@empresa.com',
      password: 'password-segura',
    });
    expect(successToastMock).toHaveBeenCalledWith('¡Bienvenido de nuevo!');
    expect(navigateByUrlMock).toHaveBeenCalledWith('/dashboard');
  });

  it('redirige a la selección de empresa cuando corresponde', async () => {
    authStatus.set('company-selection-required');

    component.form.setValue({
      email: 'usuario@empresa.com',
      password: 'password-segura',
    });

    await component.submit();

    expect(navigateByUrlMock).toHaveBeenCalledWith('/select-company');
    expect(successToastMock).not.toHaveBeenCalled();
  });

  it('muestra el error cuando falla el inicio de sesión', async () => {
    loginMock.mockRejectedValue(new Error('Correo o contraseña incorrectos.'));

    component.form.setValue({
      email: 'admin@empresa.com',
      password: 'incorrecta',
    });

    await component.submit();

    expect(component.errorMessage()).toBe('Correo o contraseña incorrectos.');
    expect(navigateByUrlMock).not.toHaveBeenCalled();
  });
});
