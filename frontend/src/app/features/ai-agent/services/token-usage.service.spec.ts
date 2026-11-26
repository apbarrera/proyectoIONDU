import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TokenUsage, TokenUsageService, monthLabel } from './token-usage.service';

const USAGE: TokenUsage = {
  monthlyLimit: 1000,
  used: 850,
  remaining: 150,
  percentUsed: 85,
  nearLimit: true,
  limitReached: false,
  history: [{ month: '2026-11', used: 850 }],
};

describe('TokenUsageService', () => {
  let service: TokenUsageService;
  let http: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({ providers: [provideHttpClient(), provideHttpClientTesting()] });
    service = TestBed.inject(TokenUsageService);
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => http.verify());

  it('carga el consumo real del backend', () => {
    service.load().subscribe();
    http.expectOne({ method: 'GET', url: '/api/ai/usage' }).flush(USAGE);
    expect(service.usage()?.used).toBe(850);
  });

  it('guarda el límite y quitarlo envía null', () => {
    service.setLimit(null).subscribe();
    const request = http.expectOne({ method: 'PUT', url: '/api/ai/usage/limit' });
    expect(request.request.body).toEqual({ monthlyLimit: null });
    request.flush({ ...USAGE, monthlyLimit: null });
    expect(service.usage()?.monthlyLimit).toBeNull();
  });

  it('muestra el mes en español', () => {
    expect(monthLabel('2026-11')).toBe('Nov 2026');
    expect(monthLabel('2027-01')).toBe('Ene 2027');
  });
});
