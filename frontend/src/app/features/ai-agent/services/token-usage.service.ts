import { HttpClient } from '@angular/common/http';
import { Injectable, inject, signal } from '@angular/core';
import { Observable, tap } from 'rxjs';
import { environment } from '../../../../environments/environment';

/** Consumo de tokens del agente de IA (RF-6.14). Solo el Administrador lo consulta. */
export interface TokenUsage {
  /** `null`: sin límite. */
  monthlyLimit: number | null;
  /** Tokens del mes actual (calendario de Ecuador). */
  used: number;
  remaining: number | null;
  percentUsed: number | null;
  /** 80 % o más del límite. */
  nearLimit: boolean;
  limitReached: boolean;
  /** Últimos 6 meses, del más antiguo al actual; `month` es `AAAA-MM`. */
  history: { month: string; used: number }[];
}

const MONTHS = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic'];

/** `2026-11` → `Nov 2026`. */
export function monthLabel(month: string): string {
  const [year, number] = month.split('-').map(Number);
  return `${MONTHS[number - 1] ?? month} ${year}`;
}

@Injectable({ providedIn: 'root' })
export class TokenUsageService {
  private readonly http = inject(HttpClient);
  private readonly baseUrl = `${environment.apiUrl}/ai/usage`;

  #usage = signal<TokenUsage | null>(null);
  readonly usage = this.#usage.asReadonly();

  load(): Observable<TokenUsage> {
    return this.http.get<TokenUsage>(this.baseUrl).pipe(tap((usage) => this.#usage.set(usage)));
  }

  /** Cambia el límite mensual; `null` lo quita (RNF-12). */
  setLimit(monthlyLimit: number | null): Observable<TokenUsage> {
    return this.http
      .put<TokenUsage>(`${this.baseUrl}/limit`, { monthlyLimit })
      .pipe(tap((usage) => this.#usage.set(usage)));
  }
}
