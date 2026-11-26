import { HttpErrorResponse } from '@angular/common/http';
import { TestBed } from '@angular/core/testing';
import { of, throwError } from 'rxjs';
import { AuthTokenResponse } from '../models/auth.model';
import { CompanyMembership, MeResponse } from '../models/company.model';
import { AuthApiService } from './auth-api.service';
import { AuthService } from './auth.service';
import { AuthTokenService } from './auth-token.service';
import { MeApiService } from './me-api.service';

const SESSION: AuthTokenResponse = {
  accessToken: 'test-access-token',
  tokenType: 'Bearer',
  expiresIn: 900,
  user: {
    id: 'user-123',
    email: 'admin@empresa.com',
    createdAt: '2026-01-01T00:00:00.000Z',
  },
};

function httpError(status: number, code?: string, message?: string): HttpErrorResponse {
  return new HttpErrorResponse({
    status,
    error: code ? { error: { code, message, details: [] } } : null,
  });
}

const COMPANY_A: CompanyMembership = {
  id: 1,
  name: 'Empresa A S.A.',
  tradeName: 'Empresa A',
  ruc: '1790000000001',
  role: 'admin',
};

const COMPANY_B: CompanyMembership = {
  id: 2,
  name: 'Empresa B S.A.',
  tradeName: 'Empresa B',
  ruc: '1790000000002',
  role: 'operator',
};

const PROFILE: MeResponse = {
  id: 'user-123',
  email: 'admin@empresa.com',
  fullName: 'Usuario Administrador',
  role: 'admin',
  tenantId: 1,
  active: true,
};

describe('AuthService', () => {
  let auth: AuthService;
  let authApi: {
    login: ReturnType<typeof vi.fn>;
    refresh: ReturnType<typeof vi.fn>;
    logout: ReturnType<typeof vi.fn>;
  };
  let meApi: {
    getCompanies: ReturnType<typeof vi.fn>;
    getMe: ReturnType<typeof vi.fn>;
  };

  beforeEach(() => {
    localStorage.clear();
    sessionStorage.clear();

    authApi = {
      login: vi.fn().mockReturnValue(of(SESSION)),
      // Sin cookie de renovación: no hay sesión que restaurar.
      refresh: vi.fn().mockReturnValue(throwError(() => httpError(401, 'SESSION_INVALID'))),
      logout: vi.fn().mockReturnValue(of(undefined)),
    };

    meApi = {
      getCompanies: vi.fn().mockReturnValue(of([COMPANY_A])),
      getMe: vi.fn().mockReturnValue(of(PROFILE)),
    };

    TestBed.configureTestingModule({
      providers: [
        { provide: AuthApiService, useValue: authApi },
        { provide: MeApiService, useValue: meApi },
      ],
    });

    auth = TestBed.inject(AuthService);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('inicia sin sesión cuando no hay cookie de renovación', async () => {
    await auth.initialize();

    expect(auth.isAuthenticated()).toBe(false);
    expect(auth.status()).toBe('unauthenticated');
    expect(meApi.getCompanies).not.toHaveBeenCalled();
  });

  it('inicia sesión y carga el perfil de una empresa', async () => {
    await auth.login({
      email: ' ADMIN@EMPRESA.COM ',
      password: 'password-segura',
    });

    expect(authApi.login).toHaveBeenCalledWith({
      email: 'admin@empresa.com',
      password: 'password-segura',
    });
    expect(meApi.getCompanies).toHaveBeenCalledOnce();
    expect(meApi.getMe).toHaveBeenCalledOnce();
    expect(auth.isAuthenticated()).toBe(true);
    expect(auth.status()).toBe('authenticated');
    expect(auth.currentUser()?.email).toBe('admin@empresa.com');
    expect(auth.currentUser()?.role).toBe('admin');
    expect(auth.defaultRouteForCurrentUser()).toBe('/dashboard');
    expect(TestBed.inject(AuthTokenService).accessToken).toBe('test-access-token');
  });

  it('rechaza credenciales incorrectas con un mensaje comprensible', async () => {
    authApi.login.mockReturnValue(
      throwError(() =>
        httpError(401, 'INVALID_CREDENTIALS', 'Correo o contraseña incorrectos.'),
      ),
    );

    await expect(
      auth.login({
        email: 'admin@empresa.com',
        password: 'incorrecta',
      }),
    ).rejects.toThrow('Correo o contraseña incorrectos.');

    expect(auth.isAuthenticated()).toBe(false);
    expect(auth.status()).toBe('unauthenticated');
  });

  it('identifica cuando el usuario no tiene empresas asignadas', async () => {
    meApi.getCompanies.mockReturnValue(of([]));

    await auth.login({
      email: 'admin@empresa.com',
      password: 'password-segura',
    });

    expect(auth.isAuthenticated()).toBe(true);
    expect(auth.status()).toBe('no-company');
    expect(meApi.getMe).not.toHaveBeenCalled();
  });

  it('solicita selección cuando el usuario tiene varias empresas', async () => {
    meApi.getCompanies.mockReturnValue(of([COMPANY_A, COMPANY_B]));

    await auth.login({
      email: 'admin@empresa.com',
      password: 'password-segura',
    });

    expect(auth.status()).toBe('company-selection-required');
    expect(meApi.getMe).not.toHaveBeenCalled();
  });

  it('restaura una sesión existente con la cookie de renovación', async () => {
    authApi.refresh.mockReturnValue(of(SESSION));

    await auth.initialize();

    expect(auth.isAuthenticated()).toBe(true);
    expect(auth.status()).toBe('authenticated');
    expect(auth.currentUser()?.id).toBe('user-123');
    expect(TestBed.inject(AuthTokenService).accessToken).toBe('test-access-token');
  });

  it('rechaza un perfil que pertenece a otra empresa', async () => {
    meApi.getMe.mockReturnValue(
      of({ ...PROFILE, tenantId: 99 }),
    );

    await expect(
      auth.login({
        email: 'admin@empresa.com',
        password: 'password-segura',
      }),
    ).rejects.toThrow(
      'El perfil recibido no corresponde a la empresa seleccionada.',
    );

    expect(auth.status()).toBe('error');
  });

  it('cierra sesión y conserva las preferencias del navegador', async () => {
    localStorage.setItem('iondu-theme', '"dark"');
    localStorage.setItem('iondu-sidebar', '{"collapsed":true,"width":264}');
    localStorage.setItem('iondu-company-id', '1');
    sessionStorage.setItem('borrador', '1');

    await auth.logout();

    expect(authApi.logout).toHaveBeenCalledOnce();
    expect(TestBed.inject(AuthTokenService).accessToken).toBeNull();
    expect(localStorage.getItem('iondu-theme')).toBe('"dark"');
    expect(localStorage.getItem('iondu-sidebar')).toBe('{"collapsed":true,"width":264}');
    expect(localStorage.getItem('iondu-company-id')).toBeNull();
    expect(sessionStorage.getItem('borrador')).toBe('1');
    expect(auth.isAuthenticated()).toBe(false);
    expect(auth.currentUser()).toBeNull();
    expect(auth.status()).toBe('unauthenticated');
  });

  it('no elimina las cachés del service worker al cerrar sesión', async () => {
    const keys = vi.fn().mockResolvedValue(['ngsw:/:db:control']);
    const deleteCache = vi.fn().mockResolvedValue(true);

    vi.stubGlobal('caches', {
      keys,
      delete: deleteCache,
    });

    await auth.logout();

    expect(keys).not.toHaveBeenCalled();
    expect(deleteCache).not.toHaveBeenCalled();
  });
  it('restablece el estado cuando no hay conexión con el servidor', async () => {
    authApi.login.mockReturnValue(throwError(() => httpError(0)));

    await expect(
      auth.login({
        email: 'admin@empresa.com',
        password: 'password-segura',
      }),
    ).rejects.toThrow(
      'No se pudo conectar con el servicio de autenticación. Comprueba tu conexión e inténtalo nuevamente.',
    );

    expect(auth.status()).toBe('unauthenticated');
    expect(auth.isAuthenticated()).toBe(false);
  });

  it('después del login no vuelve a renovar la sesión al inicializar', async () => {
    await auth.initialize();
    expect(authApi.refresh).toHaveBeenCalledTimes(1);

    await auth.login({
      email: 'admin@empresa.com',
      password: 'password-segura',
    });
    await auth.initialize();

    expect(authApi.refresh).toHaveBeenCalledTimes(1);
    expect(auth.status()).toBe('authenticated');
  });

  it('muestra el mensaje del servidor cuando la cuenta está bloqueada', async () => {
    const message = 'Demasiados intentos fallidos. Intenta de nuevo en unos minutos.';
    authApi.login.mockReturnValue(
      throwError(() => httpError(429, 'TOO_MANY_ATTEMPTS', message)),
    );

    await expect(
      auth.login({ email: 'admin@empresa.com', password: 'x' }),
    ).rejects.toThrow(message);
  });

  it('cierra la sesión local aunque el servidor no responda al logout', async () => {
    await auth.login({ email: 'admin@empresa.com', password: 'password-segura' });
    authApi.logout.mockReturnValue(throwError(() => httpError(0)));

    await auth.logout();

    expect(auth.status()).toBe('unauthenticated');
    expect(TestBed.inject(AuthTokenService).accessToken).toBeNull();
  });

  it('handleSessionExpired limpia la sesión sin llamar al servidor', async () => {
    await auth.login({ email: 'admin@empresa.com', password: 'password-segura' });

    auth.handleSessionExpired();

    expect(authApi.logout).not.toHaveBeenCalled();
    expect(auth.isAuthenticated()).toBe(false);
    expect(auth.currentUser()).toBeNull();
    expect(TestBed.inject(AuthTokenService).accessToken).toBeNull();
  });

  it('conserva la fecha de creación real de la cuenta', async () => {
    await auth.login({
      email: 'admin@empresa.com',
      password: 'password-segura',
    });

    expect(auth.currentUser()?.createdAt).toBe(SESSION.user.createdAt);
  });
});
