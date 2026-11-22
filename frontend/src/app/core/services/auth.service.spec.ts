import { TestBed } from '@angular/core/testing';
import { Session } from '@supabase/auth-js';
import { of } from 'rxjs';
import { AuthService } from './auth.service';
import { SUPABASE_AUTH } from './supabase-auth.token';
import { MeApiService } from './me-api.service';
import { CompanyMembership, MeResponse } from '../models/company.model';

const SESSION = {
  access_token: 'test-access-token',
  refresh_token: 'test-refresh-token',
  token_type: 'bearer',
  expires_in: 3600,
  expires_at: 1900000000,
  user: {
    id: 'user-123',
    app_metadata: {},
    user_metadata: {},
    aud: 'authenticated',
    created_at: '2026-01-01T00:00:00.000Z',
  },
} as unknown as Session;

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
  let supabaseAuth: {
    getSession: ReturnType<typeof vi.fn>;
    signInWithPassword: ReturnType<typeof vi.fn>;
    signOut: ReturnType<typeof vi.fn>;
  };
  let meApi: {
    getCompanies: ReturnType<typeof vi.fn>;
    getMe: ReturnType<typeof vi.fn>;
  };

  beforeEach(() => {
    localStorage.clear();
    sessionStorage.clear();

    supabaseAuth = {
      getSession: vi.fn().mockResolvedValue({
        data: { session: null },
        error: null,
      }),
      signInWithPassword: vi.fn().mockResolvedValue({
        data: { session: SESSION },
        error: null,
      }),
      signOut: vi.fn().mockResolvedValue({ error: null }),
    };

    meApi = {
      getCompanies: vi.fn().mockReturnValue(of([COMPANY_A])),
      getMe: vi.fn().mockReturnValue(of(PROFILE)),
    };

    TestBed.configureTestingModule({
      providers: [
        { provide: SUPABASE_AUTH, useValue: supabaseAuth },
        { provide: MeApiService, useValue: meApi },
      ],
    });

    auth = TestBed.inject(AuthService);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('inicia sin sesión cuando Supabase no devuelve una sesión', async () => {
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

    expect(supabaseAuth.signInWithPassword).toHaveBeenCalledWith({
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
  });

  it('rechaza credenciales incorrectas con un mensaje comprensible', async () => {
    supabaseAuth.signInWithPassword.mockResolvedValue({
      data: { session: null },
      error: new Error('Invalid login credentials'),
    });

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

  it('restaura una sesión existente y carga el perfil', async () => {
    supabaseAuth.getSession.mockResolvedValue({
      data: { session: SESSION },
      error: null,
    });

    await auth.initialize();

    expect(auth.isAuthenticated()).toBe(true);
    expect(auth.status()).toBe('authenticated');
    expect(auth.currentUser()?.id).toBe('user-123');
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

    expect(supabaseAuth.signOut).toHaveBeenCalledOnce();
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
  it('restablece el estado cuando Supabase lanza un error de conexión', async () => {
    supabaseAuth.signInWithPassword.mockRejectedValue(
      new Error('Network error'),
    );

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

  it('vuelve a inicializar la sesión después de un login', async () => {
    await auth.initialize();

    expect(supabaseAuth.getSession).toHaveBeenCalledTimes(1);

    supabaseAuth.getSession.mockResolvedValue({
      data: { session: SESSION },
      error: null,
    });

    await auth.login({
      email: 'admin@empresa.com',
      password: 'password-segura',
    });

    await auth.initialize();

    expect(supabaseAuth.getSession).toHaveBeenCalledTimes(2);
    expect(auth.status()).toBe('authenticated');
  });

  it('conserva la fecha de creación real de la cuenta de Supabase', async () => {
    await auth.login({
      email: 'admin@empresa.com',
      password: 'password-segura',
    });

    expect(auth.currentUser()?.createdAt).toBe(
      SESSION.user.created_at,
    );
  });
});
