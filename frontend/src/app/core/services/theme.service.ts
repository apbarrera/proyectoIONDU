import { Injectable, computed, effect, inject, signal } from '@angular/core';
import { StorageService } from './storage.service';

export type ThemePreference = 'light' | 'dark' | 'system';

const STORAGE_KEY = 'iondu-theme';

@Injectable({ providedIn: 'root' })
export class ThemeService {
  private storage = inject(StorageService);

  #media = window.matchMedia('(prefers-color-scheme: dark)');
  #systemPrefersDark = signal(this.#media.matches);

  readonly preference = signal<ThemePreference>(this.#readInitialPreference());

  readonly appliedTheme = computed<'light' | 'dark'>(() => {
    const pref = this.preference();
    if (pref === 'system') return this.#systemPrefersDark() ? 'dark' : 'light';
    return pref;
  });

  constructor() {
    this.#media.addEventListener('change', (e) => this.#systemPrefersDark.set(e.matches));

    effect(() => {
      document.documentElement.dataset['theme'] = this.appliedTheme();
    });
  }

  setPreference(pref: ThemePreference): void {
    this.preference.set(pref);
    this.storage.set(STORAGE_KEY, pref);
  }

  #readInitialPreference(): ThemePreference {
    const stored = this.storage.get<ThemePreference>(STORAGE_KEY);
    return stored ?? 'system';
  }
}
