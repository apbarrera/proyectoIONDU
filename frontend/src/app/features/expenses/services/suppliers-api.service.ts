import { Injectable, inject } from '@angular/core';
import { HttpClient, HttpContext, HttpErrorResponse, HttpParams } from '@angular/common/http';
import { Observable, catchError, of, switchMap, throwError } from 'rxjs';

import { environment } from '../../../../environments/environment';
import { SKIP_ERROR_TOAST } from '../../../core/utils/api-error.util';
import { PageDto, fetchAllPages } from '../../../core/utils/pagination.util';
import { Supplier } from '../models/expense.model';

export interface CreateSupplierInput {
  identification: string;
  name: string;
  email?: string | null;
  phone?: string | null;
  address?: string | null;
}

/** Campos editables de un proveedor; solo se envían los que cambian. */
export type UpdateSupplierInput = Partial<Pick<Supplier, 'identification' | 'name' | 'phone' | 'email' | 'address'>>;

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

  /** Todos los proveedores de la empresa (de 100 en 100). */
  list(): Observable<Supplier[]> {
    return fetchAllPages<Supplier>((page) =>
      this.http.get<PageDto<Supplier>>(this.baseUrl, {
        params: new HttpParams().set('page', page).set('pageSize', 100),
      }),
    );
  }

  create(input: CreateSupplierInput): Observable<Supplier> {
    return this.http.post<Supplier>(this.baseUrl, {
      identification: input.identification,
      name: input.name,
      email: input.email || null,
      phone: input.phone || null,
      address: input.address || null,
    });
  }

  /** Actualiza solo los campos enviados (`PATCH /api/suppliers/{id}`). */
  update(id: number, changes: UpdateSupplierInput): Observable<Supplier> {
    return this.http.patch<Supplier>(`${this.baseUrl}/${id}`, changes);
  }

  /** Devuelve el proveedor de ese RUC o cédula y lo crea si todavía no existe. */
  findOrCreate(input: CreateSupplierInput): Observable<Supplier> {
    return this.lookup(input.identification).pipe(
      switchMap((existing) => (existing ? of(existing) : this.create(input))),
    );
  }
}
