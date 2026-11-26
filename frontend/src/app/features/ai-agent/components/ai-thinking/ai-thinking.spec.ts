import { ComponentFixture, TestBed } from '@angular/core/testing';
import { afterEach, beforeEach, vi } from 'vitest';

import { AiThinking } from './ai-thinking';

describe('AiThinking', () => {
  let fixture: ComponentFixture<AiThinking>;

  beforeEach(async () => {
    vi.useFakeTimers();
    await TestBed.configureTestingModule({ imports: [AiThinking] }).compileComponents();
    fixture = TestBed.createComponent(AiThinking);
  });

  afterEach(() => vi.useRealTimers());

  const text = () => (fixture.nativeElement as HTMLElement).textContent?.replace(/\s+/g, ' ').trim();

  it('avanza el mensaje y muestra los segundos mientras espera', () => {
    fixture.detectChanges();
    expect(text()).toBe('Pensando…');

    vi.advanceTimersByTime(5000);
    fixture.detectChanges();
    const host = fixture.nativeElement as HTMLElement;
    expect(host.querySelector('.ai-thinking__label')?.textContent).toBe('Revisando tus categorías y productos…');
    expect(host.querySelector('.ai-thinking__seconds')?.textContent?.trim()).toBe('5 s');

    vi.advanceTimersByTime(8000);
    fixture.detectChanges();
    expect(text()).toContain('Sigue trabajando');
  });

  it('usa mensajes propios para fotos y voz', () => {
    fixture.componentRef.setInput('kind', 'imagen');
    fixture.detectChanges();
    expect(text()).toBe('Leyendo la foto…');

    fixture.componentRef.setInput('kind', 'voz');
    fixture.detectChanges();
    expect(text()).toBe('Escuchando el audio…');
  });

  it('se anuncia a los lectores de pantalla', () => {
    fixture.detectChanges();
    const status = (fixture.nativeElement as HTMLElement).querySelector('[role="status"]');
    expect(status?.getAttribute('aria-live')).toBe('polite');
  });
});
