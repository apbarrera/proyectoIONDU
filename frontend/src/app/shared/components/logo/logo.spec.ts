import { ComponentFixture, TestBed } from '@angular/core/testing';
import { Logo } from './logo';

describe('Logo', () => {
  let fixture: ComponentFixture<Logo>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({ imports: [Logo] }).compileComponents();
    fixture = TestBed.createComponent(Logo);
    fixture.detectChanges();
  });

  it('dibuja el isotipo con el color heredado del texto', () => {
    const host: HTMLElement = fixture.nativeElement;
    const svg = host.querySelector('svg');
    expect(svg?.getAttribute('fill')).toBe('currentColor');
    expect(host.querySelector('path')?.getAttribute('d')).toMatch(/^M /);
  });

  it('se expone como imagen con el nombre de la marca', () => {
    const host: HTMLElement = fixture.nativeElement;
    expect(host.getAttribute('role')).toBe('img');
    expect(host.getAttribute('aria-label')).toBe('IONDU');
  });
});
