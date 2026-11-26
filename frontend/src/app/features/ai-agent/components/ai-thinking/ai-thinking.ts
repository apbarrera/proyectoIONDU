import { Component, ElementRef, OnDestroy, OnInit, computed, inject, input, signal } from '@angular/core';
import { AiInputType } from '../../models/ai-message.model';

/** Desde qué segundo se muestra cada mensaje, según lo que envió el usuario. */
const STAGES: Record<AiInputType, { from: number; text: string }[]> = {
  texto: [
    { from: 0, text: 'Pensando' },
    { from: 4, text: 'Revisando tus categorías y productos' },
    { from: 12, text: 'Sigue trabajando; a veces tarda un poco más' },
  ],
  imagen: [
    { from: 0, text: 'Leyendo la foto' },
    { from: 6, text: 'Buscando el total, el proveedor y los productos' },
    { from: 20, text: 'Sigue trabajando; las fotos tardan un poco más' },
  ],
  voz: [
    { from: 0, text: 'Escuchando el audio' },
    { from: 6, text: 'Interpretando lo que dijiste' },
    { from: 20, text: 'Sigue trabajando; a veces tarda un poco más' },
  ],
};

/** A partir de este segundo se muestra el tiempo transcurrido. */
export const SHOW_SECONDS_FROM = 3;

/**
 * Burbuja "el agente está pensando": puntos animados, un mensaje que avanza con el
 * tiempo y los segundos transcurridos, para que se note que sigue trabajando.
 */
@Component({
  selector: 'app-ai-thinking',
  templateUrl: './ai-thinking.html',
  styleUrl: './ai-thinking.scss',
})
export class AiThinking implements OnInit, OnDestroy {
  private readonly host = inject<ElementRef<HTMLElement>>(ElementRef);

  kind = input<AiInputType>('texto');

  readonly seconds = signal(0);
  readonly label = computed(() => {
    const stages = STAGES[this.kind()];
    return [...stages].reverse().find((stage) => this.seconds() >= stage.from)?.text ?? stages[0].text;
  });
  readonly showSeconds = computed(() => this.seconds() >= SHOW_SECONDS_FROM);

  #timer: ReturnType<typeof setInterval> | undefined;

  ngOnInit(): void {
    this.host.nativeElement.scrollIntoView?.({ block: 'nearest' });
    this.#timer = setInterval(() => this.seconds.update((s) => s + 1), 1000);
  }

  ngOnDestroy(): void {
    clearInterval(this.#timer);
  }
}
