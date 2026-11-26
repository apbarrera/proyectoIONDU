import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable, inject, signal } from '@angular/core';
import { Observable, map, tap } from 'rxjs';
import { environment } from '../../../environments/environment';
import { AuditEntry, AuditFilters } from '../models/audit.model';
import { PageDto } from '../utils/pagination.util';

const PAGE_SIZE = 100;

type AuditEntryDto = Omit<AuditEntry, 'id'> & { id: number };

/**
 * Auditoría de la empresa (solo Administrador). La escribe el backend al completar cada
 * acción; desde el navegador no se puede crear ni modificar.
 */
@Injectable({ providedIn: 'root' })
export class AuditService {
  private readonly http = inject(HttpClient);
  private readonly baseUrl = `${environment.apiUrl}/audit`;

  #entries = signal<AuditEntry[]>([]);
  #total = signal(0);
  #page = 0;
  #filters: AuditFilters = {};

  readonly entries = this.#entries.asReadonly();
  readonly total = this.#total.asReadonly();

  /** Primera página (lo más reciente) con los filtros indicados. */
  load(filters: AuditFilters = {}): Observable<AuditEntry[]> {
    this.#filters = filters;
    this.#page = 0;
    this.#entries.set([]);
    return this.loadMore();
  }

  /** Página siguiente con los mismos filtros. */
  loadMore(): Observable<AuditEntry[]> {
    const page = this.#page + 1;
    let params = new HttpParams().set('page', page).set('pageSize', PAGE_SIZE);
    for (const [key, value] of Object.entries(this.#filters)) {
      if (value) params = params.set(key, value);
    }
    return this.http.get<PageDto<AuditEntryDto>>(this.baseUrl, { params }).pipe(
      map((result) => ({ ...result, items: result.items.map((dto) => ({ ...dto, id: String(dto.id) })) })),
      tap((result) => {
        this.#page = result.page;
        this.#total.set(result.total);
        this.#entries.update((list) => [...list, ...result.items]);
      }),
      map((result) => result.items),
    );
  }

  hasMore(): boolean {
    return this.#entries().length < this.#total();
  }
}
