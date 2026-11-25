import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';

import { Suppliers } from './suppliers';
import { Supplier } from '../../models/expense.model';

const supplier = (id: number, overrides: Partial<Supplier> = {}): Supplier => ({
  id,
  identification: '1790016919001',
  name: 'Corporación Favorita',
  phone: null,
  email: null,
  address: null,
  identificationWarning: null,
  ...overrides,
});

describe('Suppliers', () => {
  let component: Suppliers;
  let fixture: ComponentFixture<Suppliers>;
  let httpMock: HttpTestingController;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [Suppliers],
      providers: [provideHttpClient(), provideHttpClientTesting()],
    }).compileComponents();

    httpMock = TestBed.inject(HttpTestingController);
    fixture = TestBed.createComponent(Suppliers);
    component = fixture.componentInstance;
    await fixture.whenStable();

    httpMock
      .expectOne((r) => r.url === '/api/suppliers' && r.method === 'GET')
      .flush({ items: [supplier(1)], total: 1, page: 1, pageSize: 100 });
  });

  afterEach(() => httpMock.verify());

  it('carga los proveedores de la empresa', () => {
    expect(component.suppliers().map((s) => s.id)).toEqual([1]);
    expect(component.loading()).toBe(false);
  });

  it('al editar solo envía los campos que cambiaron', () => {
    component.openEdit(component.suppliers()[0]);
    component.form.controls.phone.setValue('022345678');
    component.save();

    const req = httpMock.expectOne('/api/suppliers/1');
    expect(req.request.method).toBe('PATCH');
    expect(req.request.body).toEqual({ phone: '022345678' });
    req.flush(supplier(1, { phone: '022345678' }));

    expect(component.suppliers()[0].phone).toBe('022345678');
    expect(component.editing()).toBeNull();
  });

  it('crea un proveedor nuevo y lo agrega al inicio', () => {
    component.openNew();
    component.form.setValue({
      identification: '1710034065',
      name: 'Juan Pérez',
      address: '',
      phone: '',
      email: 'juan@correo.ec',
    });
    component.save();

    const req = httpMock.expectOne((r) => r.url === '/api/suppliers' && r.method === 'POST');
    expect(req.request.body).toEqual({
      identification: '1710034065',
      name: 'Juan Pérez',
      email: 'juan@correo.ec',
      phone: null,
      address: null,
    });
    req.flush(
      supplier(2, { identification: '1710034065', name: 'Juan Pérez', email: 'juan@correo.ec' }),
    );

    expect(component.suppliers().map((s) => s.id)).toEqual([2, 1]);
  });

  it('no envía un RUC con un número de dígitos inválido', () => {
    component.openNew();
    component.form.setValue({
      identification: '12345',
      name: 'X',
      address: '',
      phone: '',
      email: '',
    });
    component.save();

    httpMock.expectNone((r) => r.method === 'POST');
    expect(component.fieldError('identification')).toBe(
      'Debe tener 10 dígitos (cédula) o 13 (RUC).',
    );
  });
});
