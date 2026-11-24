import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';

import { AdjustmentsService } from './adjustments.service';
import { MovementsService } from './movements.service';
import { ProductsService } from './products.service';

describe('Inventario conectado a la API', () => {
  let httpMock: HttpTestingController;

  const movementDto = (over: Record<string, unknown> = {}) => ({
    id: 31,
    productId: 5,
    productName: 'Café molido 250 g',
    unit: 'UNIDAD',
    type: 'salida',
    quantity: -2.5,
    resultingStock: 12.5,
    reason: 'Merma',
    date: '2026-11-20T10:30:00-05:00',
    createdBy: 'Ana Torres',
    ...over,
  });

  beforeEach(() => {
    TestBed.configureTestingModule({ providers: [provideHttpClient(), provideHttpClientTesting()] });
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => httpMock.verify());

  it('MovementsService descarga el historial y renombra reason a reference', () => {
    const service = TestBed.inject(MovementsService);
    service.getMovements().subscribe();
    httpMock
      .expectOne((r) => r.url === '/api/inventory/movements')
      .flush({ items: [movementDto()], total: 1, page: 1, pageSize: 100 });

    expect(service.movements()[0]).toEqual(
      expect.objectContaining({ id: '31', productId: '5', reference: 'Merma', quantity: -2.5 }),
    );
  });

  it('MovementsService registra una entrada manual y la agrega al historial', () => {
    const service = TestBed.inject(MovementsService);
    service.record({ productId: 5, type: 'entrada', quantity: 3, reason: 'Compra' }).subscribe();

    const req = httpMock.expectOne((r) => r.url === '/api/inventory/movements' && r.method === 'POST');
    expect(req.request.body).toEqual({ productId: 5, type: 'entrada', quantity: 3, reason: 'Compra' });
    req.flush(movementDto({ type: 'entrada', quantity: 3, resultingStock: 15.5, reason: 'Compra' }));

    expect(service.movements().length).toBe(1);
  });

  it('AdjustmentsService arma el historial de ajustes desde los movimientos de tipo ajuste', () => {
    const service = TestBed.inject(AdjustmentsService);
    service.getAdjustments().subscribe();

    const req = httpMock.expectOne((r) => r.url === '/api/inventory/movements');
    expect(req.request.params.get('type')).toBe('ajuste');
    req.flush({
      items: [movementDto({ type: 'ajuste', quantity: -3, resultingStock: 7, reason: 'Conteo' })],
      total: 1,
      page: 1,
      pageSize: 100,
    });

    expect(service.adjustments()[0]).toEqual(
      expect.objectContaining({ previousStock: 10, newStock: 7, quantityDelta: -3, reason: 'Conteo' }),
    );
  });

  it('AdjustmentsService envía el stock nuevo (no la diferencia) y refresca los productos', () => {
    const service = TestBed.inject(AdjustmentsService);
    const products = TestBed.inject(ProductsService);
    const refresh = vi.spyOn(products, 'refresh').mockImplementation(() => undefined);

    service.createAdjustment('5', 7, ' Conteo ').subscribe();
    const req = httpMock.expectOne('/api/inventory/adjustments');
    expect(req.request.body).toEqual({ productId: 5, newStock: 7, reason: 'Conteo' });
    req.flush({
      id: 32,
      productId: 5,
      productName: 'Café molido 250 g',
      previousStock: 10,
      newStock: 7,
      quantityDelta: -3,
      reason: 'Conteo',
      date: '2026-11-20T18:00:00-05:00',
      createdBy: 'Ana Torres',
    });

    expect(refresh).toHaveBeenCalled();
    expect(service.adjustments()[0].id).toBe('32');
  });
});
