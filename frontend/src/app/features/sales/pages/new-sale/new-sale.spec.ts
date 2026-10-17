import { ComponentFixture, TestBed } from '@angular/core/testing';

import { NewSale } from './new-sale';

describe('NewSale', () => {
  let component: NewSale;
  let fixture: ComponentFixture<NewSale>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [NewSale],
    }).compileComponents();

    fixture = TestBed.createComponent(NewSale);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('emite factura electrónica por defecto en cada venta nueva', () => {
    expect(component.emitInvoice()).toBe(true);
    expect(component.rucOrCedula()).toBe('9999999999');
  });

  it('no deja confirmar sin productos en el carrito', () => {
    expect(component.canConfirm()).toBe(false);
  });

  it('con factura activa exige una cédula (10 dígitos) o un RUC (13 dígitos)', () => {
    component.cart.set([{ productId: 'p1', productName: 'Torta', unitPrice: 25, quantity: 1, availableStock: 5 }]);
    expect(component.canConfirm()).toBe(true);

    component.rucOrCedula.set('12345');
    expect(component.idError()).not.toBe('');
    expect(component.canConfirm()).toBe(false);

    component.rucOrCedula.set('1790012345001');
    expect(component.idError()).toBe('');
    expect(component.canConfirm()).toBe(true);
  });

  it('sin factura no pide datos del cliente', () => {
    component.cart.set([{ productId: 'p1', productName: 'Torta', unitPrice: 25, quantity: 1, availableStock: 5 }]);
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
});
