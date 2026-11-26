import { Injectable, inject, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, tap } from 'rxjs';

import { environment } from '../../../environments/environment';
import { BillingSettings, Tenant, TenantChanges } from '../models/tenant.model';

/** Empresa activa del usuario (`/api/company`). Cualquier usuario la consulta; solo el Administrador la modifica. */
@Injectable({ providedIn: 'root' })
export class TenantService {
  private readonly http = inject(HttpClient);
  private readonly baseUrl = `${environment.apiUrl}/company`;

  #tenant = signal<Tenant | null>(null);
  readonly tenant = this.#tenant.asReadonly();

  getTenant(): Observable<Tenant> {
    return this.http.get<Tenant>(this.baseUrl).pipe(tap((tenant) => this.#tenant.set(tenant)));
  }

  /** Edita solo los campos enviados. El RUC no se puede cambiar. */
  updateTenant(changes: TenantChanges): Observable<Tenant> {
    return this.http.put<Tenant>(this.baseUrl, changes).pipe(tap((tenant) => this.#tenant.set(tenant)));
  }

  /** Guarda la configuración del emisor (el objeto completo). */
  saveBillingSettings(settings: BillingSettings): Observable<Tenant> {
    return this.http
      .put<Tenant>(`${this.baseUrl}/billing-settings`, settings)
      .pipe(tap((tenant) => this.#tenant.set(tenant)));
  }

  /**
   * Sube el `.p12` y su contraseña (`multipart/form-data`). El backend lo valida y lo guarda cifrado;
   * después se vuelve a pedir la empresa para actualizar el estado de la firma.
   */
  uploadCertificate(file: File, password: string): Observable<{ mensaje: string; fecha_vencimiento: string }> {
    const body = new FormData();
    body.append('archivo', file);
    body.append('clave', password);
    return this.http.put<{ mensaje: string; fecha_vencimiento: string }>(`${this.baseUrl}/certificate`, body);
  }
}
