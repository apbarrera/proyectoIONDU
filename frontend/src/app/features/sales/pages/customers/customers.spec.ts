
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import {
  HttpTestingController,
  provideHttpClientTesting,
} from '@angular/common/http/testing';

import { Customers } from './customers';
import { Customer } from '../../models/customer.model';

const customer = (id: number, overrides: Partial<Customer> = {}): Customer => ({
  id,
  identificationType: 'cedula',
  identification: '1710034065',
  name: 'Juan Pérez',
  address: null,
  phone: '0991234567',
  email: null,
  identificationWarning: null,
  ...overrides,
});

describe('Customers', () => {
  let component: Customers;
  let fixture: ComponentFixture<Customers>;
  let httpMock: HttpTestingController;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [Customers],
      providers: [provideHttpClient(), provideHttpClientTesting()],
    }).compileComponents();

    httpMock = TestBed.inject(HttpTestingController);
    fixture = TestBed.createComponent(Customers);
    component = fixture.componentInstance;
    await fixture.whenStable();

    httpMock
      .expectOne((r) => r.url === '/api/customers' && r.method === 'GET')
      .flush({ items: [customer(1)], total: 1, page: 1, pageSize: 100 });
  });

  afterEach(() => httpMock.verify());

  it('carga los clientes de la empresa', () => {
    expect(component.customers().map((c) => c.id)).toEqual([1]);
    expect(component.loading()).toBe(false);
  });

  it('al editar solo envía los campos que cambiaron', () => {
    component.openEdit(component.customers()[0]);
    component.form.controls.email.setValue('juan@correo.ec');
    component.form.controls.phone.setValue('');
    component.save();

    const req = httpMock.expectOne('/api/customers/1');
    expect(req.request.method).toBe('PATCH');
    expect(req.request.body).toEqual({
      email: 'juan@correo.ec',
      phone: null,
    });
    req.flush(customer(1, { email: 'juan@correo.ec', phone: null }));

    expect(component.customers()[0].email).toBe('juan@correo.ec');
    expect(component.editing()).toBeNull();
  });

  it('envía el tipo de identificación cuando cambia al editar', () => {
    component.openEdit(component.customers()[0]);
    component.form.controls.identificationType.setValue('pasaporte');
    component.save();

    const req = httpMock.expectOne('/api/customers/1');
    expect(req.request.method).toBe('PATCH');
    expect(req.request.body).toEqual({
      identificationType: 'pasaporte',
    });

    req.flush(customer(1, { identificationType: 'pasaporte' }));

    expect(component.customers()[0].identificationType).toBe('pasaporte');
  });

  it('sin cambios cierra el formulario sin llamar al backend', () => {
    component.openEdit(component.customers()[0]);
    component.save();

    httpMock.expectNone('/api/customers/1');
    expect(component.editing()).toBeNull();
  });

  it('crea un cliente nuevo y lo agrega al inicio', () => {
    component.openNew();
    component.form.setValue({
      identificationType: 'ruc',
      identification: '1790016919001',
      name: 'Corporación Favorita',
      address: ' ',
      phone: '',
      email: '',
    });
    component.save();

    const req = httpMock.expectOne(
      (r) => r.url === '/api/customers' && r.method === 'POST',
    );

    expect(req.request.body).toEqual({
      identificationType: 'ruc',
      identification: '1790016919001',
      name: 'Corporación Favorita',
      email: null,
      address: null,
      phone: null,
    });

    req.flush(
      customer(2, {
        identificationType: 'ruc',
        identification: '1790016919001',
        name: 'Corporación Favorita',
      }),
    );

    expect(component.customers().map((c) => c.id)).toEqual([2, 1]);
  });

  it('no envía un correo con formato inválido', () => {
    component.openNew();
    component.form.setValue({
      identificationType: 'cedula',
      identification: '1710034065',
      name: 'Ana',
      address: '',
      phone: '',
      email: 'ana@',
    });

    component.save();

    httpMock.expectNone((r) => r.method === 'POST');
    expect(component.fieldError('email')).toBe('Correo no válido.');
  });
});
