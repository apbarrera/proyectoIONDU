import { Injectable, signal } from '@angular/core';
import { Observable } from 'rxjs';
import { AuditEntry, AuditModule } from '../models/audit.model';
import { AUDIT_MOCK } from '../../mocks/audit.mock';
import { generateId } from '../utils/id.util';
import { simulateRequest } from './mock-http.util';

@Injectable({ providedIn: 'root' })
export class AuditService {
  #entries = signal<AuditEntry[]>(AUDIT_MOCK);
  readonly entries = this.#entries.asReadonly();

  getEntries(): Observable<AuditEntry[]> {
    return simulateRequest(this.#entries());
  }

  log(params: {
    userId: string;
    userName: string;
    module: AuditModule;
    action: string;
    description: string;
  }): void {
    const entry: AuditEntry = {
      id: generateId(),
      timestamp: new Date().toISOString(),
      ...params,
    };
    this.#entries.update((list) => [entry, ...list]);
  }
}
