import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';

import { AuditLog } from './audit-log';

const ENTRY = {
  id: 7,
  timestamp: '2026-11-26T09:00:00-05:00',
  userId: 'u-1',
  userName: 'Ana Torres',
  module: 'ventas',
  action: 'Registró venta',
  description: 'Venta #12 por $4.50.',
  entity: 'venta',
  entityId: '12',
};

describe('AuditLog', () => {
  let component: AuditLog;
  let fixture: ComponentFixture<AuditLog>;
  let http: HttpTestingController;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [AuditLog],
      providers: [provideHttpClient(), provideHttpClientTesting()],
    }).compileComponents();

    fixture = TestBed.createComponent(AuditLog);
    component = fixture.componentInstance;
    http = TestBed.inject(HttpTestingController);
    fixture.detectChanges();
  });

  afterEach(() => http.verify());

  it('carga lo más reciente desde la API al abrir', () => {
    const request = http.expectOne((r) => r.url === '/api/audit');
    expect(request.request.params.get('page')).toBe('1');
    request.flush({ items: [ENTRY], total: 1, page: 1, pageSize: 100 });

    expect(component.auditService.entries()[0].id).toBe('7');
    expect(component.auditService.hasMore()).toBe(false);
  });

  it('envía los filtros de módulo y fechas', () => {
    http.expectOne((r) => r.url === '/api/audit').flush({ items: [], total: 0, page: 1, pageSize: 100 });

    component.filters.setValue({ module: 'gastos', from: '2026-11-01', to: '2026-11-30' });
    component.search();

    const request = http.expectOne((r) => r.url === '/api/audit');
    expect(request.request.params.get('module')).toBe('gastos');
    expect(request.request.params.get('from')).toBe('2026-11-01');
    expect(request.request.params.get('to')).toBe('2026-11-30');
    request.flush({ items: [], total: 0, page: 1, pageSize: 100 });
  });

  it('pide la página siguiente con "Cargar más"', () => {
    http.expectOne((r) => r.url === '/api/audit').flush({ items: [ENTRY], total: 2, page: 1, pageSize: 1 });
    expect(component.auditService.hasMore()).toBe(true);

    component.loadMore();
    const request = http.expectOne((r) => r.url === '/api/audit');
    expect(request.request.params.get('page')).toBe('2');
    request.flush({ items: [{ ...ENTRY, id: 8 }], total: 2, page: 2, pageSize: 1 });

    expect(component.auditService.entries().map((e) => e.id)).toEqual(['7', '8']);
  });
});
