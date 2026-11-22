import { TestBed } from '@angular/core/testing';
import {
  HttpClient,
  provideHttpClient,
  withInterceptors,
} from '@angular/common/http';
import {
  HttpTestingController,
  provideHttpClientTesting,
  TestRequest,
} from '@angular/common/http/testing';
import { authInterceptor } from './auth.interceptor';
import { CompanyContextService } from '../services/company-context.service';
import { SUPABASE_SESSION_READER } from '../services/supabase-session.token';

const getSessionMock = vi.fn();

const COMPANY = {
  id: 1,
  name: 'Empresa A S.A.',
  tradeName: 'Empresa A',
  ruc: '1790000000001',
  role: 'admin' as const,
};

describe('authInterceptor', () => {
  let http: HttpClient;
  let httpMock: HttpTestingController;

  beforeEach(() => {
    getSessionMock.mockReset();
    getSessionMock.mockResolvedValue({
      data: {
        session: {
          access_token: 'jwt-test-iondu',
        },
      },
    });

    TestBed.configureTestingModule({
      providers: [
        provideHttpClient(withInterceptors([authInterceptor])),
        provideHttpClientTesting(),
        {
          provide: SUPABASE_SESSION_READER,
          useValue: getSessionMock,
        },
      ],
    });

    http = TestBed.inject(HttpClient);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    httpMock.verify();
  });

  it('adjunta el JWT y la empresa seleccionada a las peticiones API', async () => {
    const companyContext = TestBed.inject(CompanyContextService);
    companyContext.setCompanies([COMPANY]);

    let request: TestRequest | undefined;

    http.get('/api/me').subscribe();

    await vi.waitFor(() => {
      const matches = httpMock.match('/api/me');
      if (matches.length > 0) request = matches[0];
      expect(request).toBeDefined();
    });

    expect(request!.request.headers.get('Authorization'))
      .toBe('Bearer jwt-test-iondu');

    expect(request!.request.headers.get('X-Empresa-Id'))
      .toBe('1');

    request!.flush({});
  });

  it('adjunta el JWT pero omite la empresa al consultar las membresías', async () => {
    const companyContext = TestBed.inject(CompanyContextService);
    companyContext.setCompanies([COMPANY]);

    let request: TestRequest | undefined;

    http.get('/api/me/companies').subscribe();

    await vi.waitFor(() => {
      const matches = httpMock.match('/api/me/companies');
      if (matches.length > 0) request = matches[0];
      expect(request).toBeDefined();
    });

    expect(request!.request.headers.get('Authorization'))
      .toBe('Bearer jwt-test-iondu');

    expect(request!.request.headers.has('X-Empresa-Id'))
      .toBe(false);

    request!.flush([]);
  });

  it('no adjunta credenciales ni consulta Supabase en peticiones externas', () => {
    http.get('https://example.com/data').subscribe();

    const request = httpMock.expectOne('https://example.com/data');

    expect(request.request.headers.has('Authorization'))
      .toBe(false);

    expect(request.request.headers.has('X-Empresa-Id'))
      .toBe(false);

    expect(getSessionMock).not.toHaveBeenCalled();

    request.flush({});
  });
});
