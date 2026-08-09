import { Injectable, computed, signal } from '@angular/core';

@Injectable({ providedIn: 'root' })
export class TokenUsageService {
  #used = signal(72450);
  readonly used = this.#used.asReadonly();
  readonly limit = 100000;

  readonly percentUsed = computed(() => Math.min(100, Math.round((this.#used() / this.limit) * 1000) / 10));

  readonly history = [
    { month: 'Mayo 2026', used: 58200 },
    { month: 'Junio 2026', used: 64100 },
    { month: 'Julio 2026', used: 69300 },
    { month: 'Agosto 2026', used: 72450 },
  ];

  consume(tokens: number): void {
    this.#used.update((n) => Math.min(this.limit, n + tokens));
  }
}
