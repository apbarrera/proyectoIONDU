import { EMPTY, Observable, expand, reduce } from 'rxjs';

/** Página tal como la devuelve el backend: `{ items, total, page, pageSize }` (API.md, sección 1). */
export interface PageDto<T> {
  items: T[];
  total: number;
  page: number;
  pageSize: number;
}

/** Pide página tras página hasta juntar todos los elementos. */
export function fetchAllPages<T>(getPage: (page: number) => Observable<PageDto<T>>): Observable<T[]> {
  return getPage(1).pipe(
    expand((result) => (result.page * result.pageSize < result.total ? getPage(result.page + 1) : EMPTY)),
    reduce((all, result) => [...all, ...result.items], [] as T[]),
  );
}
