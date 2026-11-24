import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';

import { SalesHistory } from './sales-history';

const saleDto = (id: number, date: string) => ({
  id,
  date,
  customerId: null,
  customerName: 'CONSUMIDOR FINAL',
  customerIdentification: null,
  items: [{ productId: 12, productName: 'Café', quantity: 1, unitPrice: 4, subtotal: 4 }],
  subtotal: 4,
  ivaAmount: 0.6,
  total: 4.6,
  paymentMethod: 'tarjeta_credito',
  status: 'completada',
  observation: null,
});

describe('SalesHistory', () => {
  let component: SalesHistory;
  let fixture: ComponentFixture<SalesHistory>;
  let httpMock: HttpTestingController;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [SalesHistory],
      providers: [provideHttpClient(), provideHttpClientTesting()],
    }).compileComponents();

    httpMock = TestBed.inject(HttpTestingController);
    fixture = TestBed.createComponent(SalesHistory);
    component = fixture.componentInstance;
    await fixture.whenStable();

    httpMock.expectOne((r) => r.url === '/api/sales').flush({
      items: [saleDto(2, '2026-11-22T10:00:00-05:00'), saleDto(1, '2026-11-21T10:00:00-05:00')],
      total: 2,
      page: 1,
      pageSize: 100,
    });
  });

  it('carga las ventas desde el backend', () => {
    expect(component).toBeTruthy();
    expect(component.rows().map((row) => row.id)).toEqual(['2', '1']);
    expect(component.rows()[0].folio).toBe('000002');
    expect(component.loading()).toBe(false);
  });

  it('sin facturas emitidas, todas las ventas aparecen como "Sin factura"', () => {
    const counts = component.counts();
    expect(counts['none']).toBe(2);
    expect(counts['authorized'] + counts['pending'] + counts['rejected'] + counts['none']).toBe(counts['all']);
  });

  it('emite la factura de una venta y la une a su fila', () => {
    component.issueInvoice(component.rows()[0]);

    const req = httpMock.expectOne('/api/sales/2/invoice');
    expect(req.request.method).toBe('POST');
    req.flush({
      id: 7,
      saleId: 2,
      invoiceNumber: '001-001-000000007',
      accessKey: '1'.repeat(49),
      authorizationStatus: 'autorizada',
      authorizationNumber: '1'.repeat(49),
      authorizationDate: '2026-11-22T10:01:00-05:00',
      messages: [],
      issueDate: '2026-11-22T10:00:30-05:00',
      subtotal: 4,
      taxes: 0.6,
      total: 4.6,
    });

    expect(component.rows()[0].invoice?.status).toBe('autorizada');
    expect(component.rows()[1].invoice).toBeUndefined();
    component.filter.set('authorized');
    expect(component.visibleRows().length).toBe(1);
  });
});
