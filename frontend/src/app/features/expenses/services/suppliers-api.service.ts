import { Injectable, inject } from '@angular/core';
import { HttpClient, HttpContext, HttpErrorResponse, HttpParams } from '@angular/common/http';
import { Observable, catchError, of, switchMap, throwError } from 'rxjs';

import { environment } from '../../../../environments/environment';
import { SKIP_ERROR_TOAST } from '../../../core/utils/api-error.util';
import { Supplier } from '../models/expense.model';

export interface CreateSupplierInput {
  identification: string;
  name: string;
  email?: string | null;
}

@Injectable({ providedIn: 'root' })
export class SuppliersApiService {
  private readonly http = inject(HttpClient);
  private readonly baseUrl = `${environment.apiUrl}/suppliers`;

  /** Busca por RUC o cédula exactos. Devuelve `null` si no existe (404). */
  lookup(identification: string): Observable<Supplier | null> {
    return this.http
      .get<Supplier>(`${this.baseUrl}/lookup`, {
        params: new HttpParams().set('identification', identification),
        // Un 404 aquí es normal (proveedor nuevo): no debe mostrar un aviso de error.
        context: new HttpContext().set(SKIP_ERROR_TOAST, true),
      })
      .pipe(
        catchError((error: HttpErrorResponse) => (error.status === 404 ? of(null) : throwError(() => error))),
      );
  }

  create(input: CreateSupplierInput): Observable<Supplier> {
    return this.http.post<Supplier>(this.baseUrl, {
      identification: input.identification,
      name: input.name,
      email: input.email || null,
    });
  }

  /** Devuelve el proveedor de ese RUC o cédula y lo crea si todavía no existe. */
  findOrCreate(input: CreateSupplierInput): Observable<Supplier> {
    return this.lookup(input.identification).pipe(
      switchMap((existing) => (existing ? of(existing) : this.create(input))),
    );
  }
}
