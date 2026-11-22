import { signal, WritableSignal } from '@angular/core';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { Router } from '@angular/router';
import { AuthService, AuthStatus } from '../../../../core/services/auth.service';
import { AuthError } from './auth-error';

describe('AuthError', () => {
  let component: AuthError;
  let fixture: ComponentFixture<AuthError>;
  let authStatus: WritableSignal<AuthStatus>;
  let initializeMock: ReturnType<typeof vi.fn>;
  let logoutMock: ReturnType<typeof vi.fn>;
  let defaultRouteMock: ReturnType<typeof vi.fn>;
  let navigateByUrlMock: ReturnType<typeof vi.fn>;

  beforeEach(async () => {
    authStatus = signal<AuthStatus>('authenticated');
    initializeMock = vi.fn().mockResolvedValue(undefined);
    logoutMock = vi.fn().mockResolvedValue(undefined);
    defaultRouteMock = vi.fn().mockReturnValue('/dashboard');
    navigateByUrlMock = vi.fn().mockResolvedValue(true);

    await TestBed.configureTestingModule({
      imports: [AuthError],
      providers: [
        {
          provide: AuthService,
          useValue: {
            initialize: initializeMock,
            logout: logoutMock,
            status: authStatus,
            defaultRouteForCurrentUser: defaultRouteMock,
          },
        },
        {
          provide: Router,
          useValue: { navigateByUrl: navigateByUrlMock },
        },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(AuthError);
    component = fixture.componentInstance;
    fixture.detectChanges();
    await fixture.whenStable();
  });

  it('crea el componente', () => {
    expect(component).toBeTruthy();
  });

  it('recupera la sesión y redirige al dashboard', async () => {
    await component.retry();

    expect(initializeMock).toHaveBeenCalledTimes(1);
    expect(defaultRouteMock).toHaveBeenCalled();
    expect(navigateByUrlMock).toHaveBeenCalledWith('/dashboard');
    expect(component.errorMessage()).toBeNull();
    expect(component.retrying()).toBe(false);
  });

  it('redirige a la selección de empresa cuando corresponde', async () => {
    authStatus.set('company-selection-required');

    await component.retry();

    expect(navigateByUrlMock).toHaveBeenCalledWith('/select-company');
  });

  it('redirige a la pantalla de empresa no asignada', async () => {
    authStatus.set('no-company');

    await component.retry();

    expect(navigateByUrlMock).toHaveBeenCalledWith('/no-company');
  });

  it('redirige al login cuando no existe una sesión', async () => {
    authStatus.set('unauthenticated');

    await component.retry();

    expect(navigateByUrlMock).toHaveBeenCalledWith('/login');
  });

  it('muestra un mensaje si falla la recuperación de sesión', async () => {
    initializeMock.mockRejectedValue(new Error('Network error'));

    await component.retry();

    expect(component.errorMessage()).toBe(
      'No pudimos conectar con el servicio. Comprueba tu conexión e inténtalo nuevamente.',
    );
    expect(navigateByUrlMock).not.toHaveBeenCalled();
    expect(component.retrying()).toBe(false);
  });

  it('cierra la sesión y redirige al login', async () => {
    await component.logout();

    expect(logoutMock).toHaveBeenCalledTimes(1);
    expect(navigateByUrlMock).toHaveBeenCalledWith('/login');
  });
});
