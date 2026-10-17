import { Injectable } from '@angular/core';
import { Observable, of } from 'rxjs';
import { delay } from 'rxjs/operators';
import { InvoiceStatus } from '../models/invoice.model';

export interface SriSubmissionResult {
  status: InvoiceStatus;
  claveAcceso: string;
  rejectionReason?: string;
}

/**
 * Stand-in for the future "Angular → API Python → adaptador de facturación → SRI" chain.
 * Angular must never talk to the SRI directly — this service is the seam where a real
 * HTTP call to the billing microservice will replace the simulated response below.
 */
@Injectable({ providedIn: 'root' })
export class BillingAdapterService {
  submit(invoiceId: string): Observable<SriSubmissionResult> {
    const approved = Math.random() > 0.12;
    const claveAcceso = this.#generateAccessKey(invoiceId);

    return of(
      approved
        ? { status: 'autorizada' as const, claveAcceso }
        : {
            status: 'rechazada' as const,
            claveAcceso,
            rejectionReason: 'El RUC del cliente no consta como registro válido en el SRI (simulado).',
          },
    ).pipe(delay(1500 + Math.random() * 1000));
  }

  #generateAccessKey(seed: string): string {
    const digits = seed
      .split('')
      .map((c) => c.charCodeAt(0) % 10)
      .join('')
      .padEnd(49, '0')
      .slice(0, 49);
    return `${digits}1`;
  }
}
