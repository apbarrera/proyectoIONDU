import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';

import { CustomersApiService, FINAL_CONSUMER_ID } from './customers-api.service';

describe('CustomersApiService', () => {
  let service: CustomersApiService;
  let httpMock: HttpTestingController;

  const customer = {
    id: 5,
    identificationType: 'cedula',
    identification: '1710000009',
    name: 'Juan Pérez',
    address: null,
    phone: null,
    email: null,
    identificationWarning: null,
  };

  beforeEach(() => {
    TestBed.configureTestingModule({ providers: [provideHttpClient(), provideHttpClientTesting()] });
    service = TestBed.inject(CustomersApiService);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => httpMock.verify());

  it('el consumidor final no se guarda: no hace ninguna petición', () => {
    let result: unknown = 'sin respuesta';
    service.findOrCreate({ identification: FINAL_CONSUMER_ID, name: 'X' }).subscribe((c) => (result = c));
    expect(result).toBeNull();
  });

  it('lookup devuelve null cuando el cliente no existe (404)', () => {
    let result: unknown = 'sin respuesta';
    service.lookup('1710000009').subscribe((c) => (result = c));
    httpMock
      .expectOne((r) => r.url === '/api/customers/lookup')
      .flush(null, { status: 404, statusText: 'Not Found' });
    expect(result).toBeNull();
  });

  it('findOrCreate crea el cliente si no existe', () => {
    let result: { id: number } | null = null;
    service
      .findOrCreate({ identification: '1710000009', name: 'Juan Pérez', email: '' })
      .subscribe((c) => (result = c));

    httpMock
      .expectOne((r) => r.url === '/api/customers/lookup')
      .flush(null, { status: 404, statusText: 'Not Found' });
    const create = httpMock.expectOne((r) => r.url === '/api/customers' && r.method === 'POST');
    expect(create.request.body).toEqual({
      identification: '1710000009',
      name: 'Juan Pérez',
      email: null,
      address: null,
      phone: null,
    });
    create.flush(customer);

    expect(result!.id).toBe(5);
  });

  it('findOrCreate reutiliza el cliente existente', () => {
    let result: { id: number } | null = null;
    service.findOrCreate({ identification: '1710000009', name: 'Otro nombre' }).subscribe((c) => (result = c));
    httpMock.expectOne((r) => r.url === '/api/customers/lookup').flush(customer);
    expect(result!.id).toBe(5);
  });
});
