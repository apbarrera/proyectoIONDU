import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';

import { NewExpense } from './new-expense';

describe('NewExpense', () => {
  let component: NewExpense;
  let fixture: ComponentFixture<NewExpense>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [NewExpense],
      providers: [provideHttpClient(), provideHttpClientTesting()],
    }).compileComponents();

    fixture = TestBed.createComponent(NewExpense);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('valida la compra que suma al inventario antes de guardar (RF-4.4)', () => {
    component.addsStock.set(true);
    expect(component.purchaseError()).toContain('al menos un producto');

    component.addRow();
    const [row] = component.rows();
    expect(component.purchaseError()).toContain('Elige el producto');

    component.updateRow(row.key, { productId: '7', quantity: 0 });
    expect(component.purchaseError()).toContain('mayor que 0');

    component.updateRow(row.key, { quantity: 5 });
    expect(component.purchaseError()).toBe('');

    component.addRow();
    component.updateRow(component.rows()[1].key, { productId: '7', quantity: 1 });
    expect(component.purchaseError()).toContain('no puede repetirse');

    component.removeRow(component.rows()[1].key);
    expect(component.purchaseError()).toBe('');
  });

  it('sin "Suma al inventario" no exige productos', () => {
    component.rows.set([]);
    component.addsStock.set(false);
    expect(component.purchaseError()).toBe('');
  });
});
