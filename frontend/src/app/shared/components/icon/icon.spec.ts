import { ComponentFixture, TestBed } from '@angular/core/testing';
import { Icon } from './icon';

describe('Icon', () => {
  let fixture: ComponentFixture<Icon>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({ imports: [Icon] }).compileComponents();
    fixture = TestBed.createComponent(Icon);
  });

  it('renderiza el svg del ícono pedido y lo oculta a lectores de pantalla', () => {
    fixture.componentRef.setInput('name', 'dashboard');
    fixture.detectChanges();
    const host: HTMLElement = fixture.nativeElement;
    expect(host.querySelector('svg')).not.toBeNull();
    expect(host.getAttribute('aria-hidden')).toBe('true');
  });

  it('con label se expone como imagen accesible', () => {
    fixture.componentRef.setInput('name', 'warning');
    fixture.componentRef.setInput('label', 'Advertencia');
    fixture.detectChanges();
    const host: HTMLElement = fixture.nativeElement;
    expect(host.getAttribute('role')).toBe('img');
    expect(host.getAttribute('aria-label')).toBe('Advertencia');
    expect(host.getAttribute('aria-hidden')).toBeNull();
  });
});
