import { ComponentFixture, TestBed } from '@angular/core/testing';
import { Switch } from './switch';

describe('Switch', () => {
  let fixture: ComponentFixture<Switch>;
  let button: HTMLButtonElement;

  beforeEach(async () => {
    await TestBed.configureTestingModule({ imports: [Switch] }).compileComponents();
    fixture = TestBed.createComponent(Switch);
    fixture.componentRef.setInput('label', 'Emitir factura electrónica');
    fixture.detectChanges();
    button = fixture.nativeElement.querySelector('button');
  });

  it('se expone como interruptor apagado por defecto', () => {
    expect(button.getAttribute('role')).toBe('switch');
    expect(button.getAttribute('aria-checked')).toBe('false');
  });

  it('cambia de estado al hacer clic y lo anuncia con aria-checked', () => {
    button.click();
    fixture.detectChanges();
    expect(fixture.componentInstance.checked()).toBe(true);
    expect(button.getAttribute('aria-checked')).toBe('true');
  });

  it('no cambia cuando está deshabilitado', () => {
    fixture.componentRef.setInput('disabled', true);
    fixture.detectChanges();
    fixture.componentInstance.toggle();
    expect(fixture.componentInstance.checked()).toBe(false);
  });
});
