import { Injectable, signal } from '@angular/core';
import { Observable } from 'rxjs';
import { Tenant } from '../models/tenant.model';
import { TENANT_MOCK } from '../../mocks/tenant.mock';
import { simulateRequest } from './mock-http.util';

/**
 * IONDU is multi-tenant SaaS: User → Empresa/Tenant → data. Only one seeded tenant exists
 * today and nothing filters on tenantId yet, but every mock entity carries it so real
 * tenant scoping can be introduced later without reshaping the models.
 */
@Injectable({ providedIn: 'root' })
export class TenantService {
  #tenant = signal<Tenant>(TENANT_MOCK);
  readonly tenant = this.#tenant.asReadonly();

  getTenant(): Observable<Tenant> {
    return simulateRequest(this.#tenant());
  }

  updateTenant(changes: Partial<Tenant>): Observable<Tenant> {
    this.#tenant.update((current) => ({ ...current, ...changes }));
    return simulateRequest(this.#tenant());
  }
}
