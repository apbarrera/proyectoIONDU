import { TestBed } from '@angular/core/testing';
import {
  HttpClient,
  HttpErrorResponse,
  provideHttpClient,
  withInterceptors,
} from '@angular/common/http';
import {
  HttpTestingController,
  provideHttpClientTesting,
  TestRequest,
} from '@angular/common/http/testing';
import { Router } from '@angular/router';
import { of, throwError } from 'rxjs';
import { authInterceptor } from './auth.interceptor';
import { AuthTokenResponse } from '../models/auth.model';
import { AuthApiService } from '../services/auth-api.service';
import { AuthService } from '../services/auth.service';
import { AuthTokenService } from '../services/auth-token.service';
import { CompanyContextService } from '../services/company-context.service';

const COMPANY = {
  id: 1,
  name: 'Empresa A S.A.',
  tradeName: 'Empresa A',
  ruc: '1790000000001',
  role: 'admin' as const,
};

function session(accessToken: string, expiresIn = 900): AuthTokenResponse {
  return {
    accessToken,
    tokenType: 'Bearer',
    expiresIn,
    user: { id: 'user-123', email: 'ana@empresa.ec', createdAt: '2026-01-01T00:00:00Z' },
  };
}

const UNAUTHORIZED = { status: 401, statusText: 'Unauthorized' };
const TOKEN_EXPIRED_BODY = {
  error: { code: 'TOKEN_EXPIRED', message: 'Tu sesión expiró.', details: [] },
};

describe('authInterceptor', () => {
  let http: HttpClient;
  let httpMock: HttpTestingController;
  let tokens: AuthTokenService;
  let authApi: { refresh: ReturnType<typeof vi.fn> };
  let auth: { handleSessionExpired: ReturnType<typeof vi.fn> };
  let router: { navigateByUrl: ReturnType<typeof vi.fn> };

  beforeEach(() => {
    authApi = { refresh: vi.fn().mockReturnValue(of(session('jwt-renovado'))) };
    auth = { handleSessionExpired: vi.fn() };
    router = { navigateByUrl: vi.fn().mockResolvedValue(true) };

    TestBed.configureTestingModule({
      providers: [
        provideHttpClient(withInterceptors([authInterceptor])),
        provideHttpClientTesting(),
        { provide: AuthApiService, useValue: authApi },
        { provide: AuthService, useValue: auth },
        { provide: Router, useValue: router },
      ],
    });

    http = TestBed.inject(HttpClient);
    httpMock = TestBed.inject(HttpTestingController);
    tokens = TestBed.inject(AuthTokenService);
    tokens.set(session('jwt-test-iondu'));
  });

  afterEach(() => {
    httpMock.verify();
  });

  async function nextRequest(url: string): Promise<TestRequest> {
    let request: TestRequest | undefined;
    await vi.waitFor(() => {
      const matches = httpMock.match(url);
      if (matches.length > 0) request = matches[0];
      expect(request).toBeDefined();
    });
    return request!;
  }

  it('adjunta el JWT y la empresa seleccionada a las peticiones API', async () => {
    TestBed.inject(CompanyContextService).setCompanies([COMPANY]);

    http.get('/api/me').subscribe();
    const request = await nextRequest('/api/me');

    expect(request.request.headers.get('Authorization')).toBe('Bearer jwt-test-iondu');
    expect(request.request.headers.get('X-Empresa-Id')).toBe('1');
    request.flush({});
  });

  it('adjunta el JWT pero omite la empresa al consultar las membresías', async () => {
    TestBed.inject(CompanyContextService).setCompanies([COMPANY]);

    http.get('/api/me/companies').subscribe();
    const request = await nextRequest('/api/me/companies');

    expect(request.request.headers.get('Authorization')).toBe('Bearer jwt-test-iondu');
    expect(request.request.headers.has('X-Empresa-Id')).toBe(false);
    request.flush([]);
  });

  it('no adjunta credenciales en peticiones externas', () => {
    http.get('https://example.com/data').subscribe();

    const request = httpMock.expectOne('https://example.com/data');
    expect(request.request.headers.has('Authorization')).toBe(false);
    expect(request.request.headers.has('X-Empresa-Id')).toBe(false);
    request.flush({});
  });

  it('no adjunta el token de acceso a /api/auth (usa la cookie)', () => {
    http.post('/api/auth/refresh', null).subscribe();

    const request = httpMock.expectOne('/api/auth/refresh');
    expect(request.request.headers.has('Authorization')).toBe(false);
    request.flush({});
  });

  it('si el token venció, lo renueva una vez y repite la petición', async () => {
    let result: unknown;
    http.get('/api/products').subscribe((body) => (result = body));

    (await nextRequest('/api/products')).flush(TOKEN_EXPIRED_BODY, UNAUTHORIZED);
    const retry = await nextRequest('/api/products');

    expect(authApi.refresh).toHaveBeenCalledOnce();
    expect(retry.request.headers.get('Authorization')).toBe('Bearer jwt-renovado');
    retry.flush({ items: [] });
    expect(result).toEqual({ items: [] });
  });

  it('si la renovación falla, cierra la sesión y lleva al login', async () => {
    authApi.refresh.mockReturnValue(throwError(() => new HttpErrorResponse(UNAUTHORIZED)));
    let error: HttpErrorResponse | undefined;
    http.get('/api/products').subscribe({ error: (e) => (error = e) });

    (await nextRequest('/api/products')).flush(TOKEN_EXPIRED_BODY, UNAUTHORIZED);

    await vi.waitFor(() => expect(error?.status).toBe(401));
    expect(auth.handleSessionExpired).toHaveBeenCalledOnce();
    expect(router.navigateByUrl).toHaveBeenCalledWith('/login');
  });

  it('otros errores 401 no disparan la renovación', async () => {
    let error: HttpErrorResponse | undefined;
    http.get('/api/products').subscribe({ error: (e) => (error = e) });

    (await nextRequest('/api/products')).flush(
      { error: { code: 'UNAUTHENTICATED', message: 'Inicia sesión.', details: [] } },
      UNAUTHORIZED,
    );

    await vi.waitFor(() => expect(error?.status).toBe(401));
    expect(authApi.refresh).not.toHaveBeenCalled();
  });

  it('renueva antes de enviar cuando el token está por vencer', async () => {
    tokens.set(session('jwt-casi-vencido', 10));

    http.get('/api/products').subscribe();
    const request = await nextRequest('/api/products');

    expect(authApi.refresh).toHaveBeenCalledOnce();
    expect(request.request.headers.get('Authorization')).toBe('Bearer jwt-renovado');
    request.flush({});
  });

  it('varias peticiones con el token por vencer comparten una sola renovación', async () => {
    tokens.set(session('jwt-casi-vencido', 10));

    http.get('/api/products').subscribe();
    http.get('/api/customers').subscribe();

    (await nextRequest('/api/products')).flush({});
    (await nextRequest('/api/customers')).flush({});
    expect(authApi.refresh).toHaveBeenCalledOnce();
  });
});
