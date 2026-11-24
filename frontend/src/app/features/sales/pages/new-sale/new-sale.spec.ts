import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';

import { NewSale } from './new-sale';

describe('NewSale', () => {
  let component: NewSale;
  let fixture: ComponentFixture<NewSale>;
  let httpMock: HttpTestingController;

  const line = { productId: '1', productName: 'Torta', unitPrice: 25, quantity: 1, availableStock: 5 };

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [NewSale],
      providers: [provideHttpClient(), provideHttpClientTesting()],
    }).compileComponents();

    httpMock = TestBed.inject(HttpTestingController);
    fixture = TestBed.createComponent(NewSale);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('should create y pide los productos al backend', () => {
    expect(component).toBeTruthy();
    expect(httpMock.match((r) => r.url === '/api/products').length).toBe(1);
  });

  it('emite factura electrónica por defecto con el consumidor final de 13 nueves', () => {
    expect(component.emitInvoice()).toBe(true);
    expect(component.rucOrCedula()).toBe('9999999999999');
    expect(component.idError()).toBe('');
  });

  it('no deja confirmar sin productos en el carrito', () => {
    expect(component.canConfirm()).toBe(false);
  });

  it('con factura activa exige una cédula (10 dígitos) o un RUC (13 dígitos)', () => {
    component.cart.set([line]);
    expect(component.canConfirm()).toBe(true);

    component.rucOrCedula.set('12345');
    expect(component.idError()).not.toBe('');
    expect(component.canConfirm()).toBe(false);
  });

  it('un cliente nuevo con identificación propia necesita nombre para registrarse', () => {
    component.cart.set([line]);
    component.onIdentificationChange('1790012345001');
    httpMock
      .expectOne((r) => r.url === '/api/customers/lookup')
      .flush(null, { status: 404, statusText: 'Not Found' });

    expect(component.nameError()).not.toBe('');
    expect(component.canConfirm()).toBe(false);

    component.customerName.set('Cafetería Buen Día');
    expect(component.nameError()).toBe('');
    expect(component.canConfirm()).toBe(true);
  });

  it('autocompleta el cliente cuando ya existe', () => {
    component.onIdentificationChange('1710000009');
    httpMock.expectOne((r) => r.url === '/api/customers/lookup').flush({
      id: 5,
      identificationType: 'cedula',
      identification: '1710000009',
      name: 'Juan Pérez',
      address: null,
      phone: null,
      email: 'juan@correo.com',
      identificationWarning: null,
    });

    expect(component.foundCustomer()?.id).toBe(5);
    expect(component.customerName()).toBe('Juan Pérez');
    expect(component.email()).toBe('juan@correo.com');
    expect(component.nameError()).toBe('');
  });

  it('sin factura no pide datos del cliente', () => {
    component.cart.set([line]);
    component.rucOrCedula.set('abc');
    component.emitInvoice.set(false);

    expect(component.idError()).toBe('');
    expect(component.canConfirm()).toBe(true);
  });

  it('valida el correo solo si se escribió uno', () => {
    component.email.set('');
    expect(component.emailError()).toBe('');

    component.email.set('no-es-un-correo');
    expect(component.emailError()).not.toBe('');

    component.email.set('cliente@empresa.com');
    expect(component.emailError()).toBe('');
  });

  it('registra la venta enviando productId y cantidad, sin precio, y con consumidor final como null', () => {
    component.cart.set([{ ...line, productId: '12', quantity: 2 }]);
    component.confirmSale();

    const req = httpMock.expectOne((r) => r.url === '/api/sales' && r.method === 'POST');
    expect(req.request.body).toEqual({
      customerId: null,
      items: [{ productId: 12, quantity: 2, discount: 0 }],
      paymentMethod: 'efectivo',
      observation: null,
    });
  });
});
