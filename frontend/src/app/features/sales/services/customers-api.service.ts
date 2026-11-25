import { Injectable, inject } from '@angular/core';
import { HttpClient, HttpContext, HttpErrorResponse, HttpParams } from '@angular/common/http';
import { Observable, catchError, of, switchMap, throwError } from 'rxjs';

import { environment } from '../../../../environments/environment';
import { SKIP_ERROR_TOAST } from '../../../core/utils/api-error.util';
import { CreateCustomerInput, Customer } from '../models/customer.model';

/** Identificación del consumidor final que exige el SRI (13 nueves). */
export const FINAL_CONSUMER_ID = '9999999999999';

@Injectable({ providedIn: 'root' })
export class CustomersApiService {
  private readonly http = inject(HttpClient);
  private readonly baseUrl = `${environment.apiUrl}/customers`;

  /** Busca por identificación exacta. Devuelve `null` si el cliente no existe (404). */
  lookup(identification: string): Observable<Customer | null> {
    return this.http
      .get<Customer>(`${this.baseUrl}/lookup`, {
        params: new HttpParams().set('identification', identification),
        // Un 404 aquí es normal (cliente nuevo): no debe mostrar un aviso de error.
        context: new HttpContext().set(SKIP_ERROR_TOAST, true),
      })
      .pipe(
        catchError((error: HttpErrorResponse) =>
          error.status === 404 ? of(null) : throwError(() => error),
        ),
      );
  }

  create(input: CreateCustomerInput): Observable<Customer> {
    return this.http.post<Customer>(this.baseUrl, {
      identification: input.identification,
      name: input.name,
      email: input.email || null,
    });
  }

  /**
   * Devuelve el cliente de esa identificación y lo crea si todavía no existe.
   * El consumidor final no se guarda como cliente: devuelve `null` (la venta usa `customerId: null`).
   */
  findOrCreate(input: CreateCustomerInput): Observable<Customer | null> {
    if (input.identification === FINAL_CONSUMER_ID) {
      return of(null);
    }

    return this.lookup(input.identification).pipe(
      switchMap((existing) => (existing ? of(existing) : this.create(input))),
    );
  }
}
