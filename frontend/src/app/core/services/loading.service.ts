import { Injectable, computed, signal } from '@angular/core';

@Injectable({ providedIn: 'root' })
export class LoadingService {
  #count = signal(0);
  readonly isLoading = computed(() => this.#count() > 0);

  start(): void {
    this.#count.update((n) => n + 1);
  }

  stop(): void {
    this.#count.update((n) => Math.max(0, n - 1));
  }
}
