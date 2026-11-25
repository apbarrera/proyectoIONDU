import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';

import { SalesService } from './sales.service';

describe('SalesService', () => {
  let service: SalesService;
  let httpMock: HttpTestingController;

  const dto = (id: number) => ({
    id,
    date: '2026-11-22T10:00:00-05:00',
    customerId: 5,
    customerName: 'Juan Pérez',
    customerIdentification: '1710000009',
    items: [
      { productId: 12, productName: 'Café', quantity: 2, unitPrice: 4.5, subtotal: 9 },
      { productId: null, productName: 'Instalación', quantity: 1, unitPrice: 15, subtotal: 15 },
    ],
    subtotal: 24,
    ivaAmount: 3.6,
    total: 27.6,
    paymentMethod: 'efectivo',
    status: 'completada',
    observation: 'Entrega',
  });

  beforeEach(() => {
    TestBed.configureTestingModule({ providers: [provideHttpClient(), provideHttpClientTesting()] });
    service = TestBed.inject(SalesService);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => httpMock.verify());

  it('descarga todas las páginas del historial', () => {
    let result: unknown[] = [];
    service.getSales().subscribe((sales) => (result = sales));

    httpMock
      .expectOne((r) => r.params.get('page') === '1')
      .flush({ items: [dto(2)], total: 2, page: 1, pageSize: 1 });
    httpMock
      .expectOne((r) => r.params.get('page') === '2')
      .flush({ items: [dto(1)], total: 2, page: 2, pageSize: 1 });

    expect(result.length).toBe(2);
    expect(service.sales().length).toBe(2);
    expect(service.totalRevenue()).toBeCloseTo(55.2);
  });

  it('convierte las líneas de concepto libre (sin producto) a productId vacío', () => {
    service.getSales().subscribe();
    httpMock.expectOne(() => true).flush({ items: [dto(1)], total: 1, page: 1, pageSize: 100 });

    expect(service.sales()[0].items.map((i) => i.productId)).toEqual(['12', '']);
  });

  it('createSale envía el cuerpo del contrato y agrega la venta al inicio', () => {
    service
      .createSale({
        customerId: 5,
        items: [{ productId: 12, quantity: 2 }],
        paymentMethod: 'efectivo',
        observation: ' Entrega ',
      })
      .subscribe((sale) => expect(sale.folio).toBe('000009'));

    const req = httpMock.expectOne('/api/sales');
    expect(req.request.body).toEqual({
      customerId: 5,
      items: [{ productId: 12, quantity: 2, discount: 0 }],
      paymentMethod: 'efectivo',
      observation: 'Entrega',
    });
    req.flush(dto(9));

    expect(service.sales()[0].id).toBe('9');
  });
});
