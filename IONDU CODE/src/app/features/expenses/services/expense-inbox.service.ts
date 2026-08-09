import { Injectable, inject, signal } from '@angular/core';
import { Observable } from 'rxjs';
import { EmailExpenseDraft } from '../models/email-draft.model';
import { EMAIL_DRAFTS_MOCK } from '../../../mocks/email-inbox.mock';
import { simulateRequest } from '../../../core/services/mock-http.util';
import { ExpensesService } from './expenses.service';

/** Stands in for a future real inbox-scanning service (IMAP/Gmail API → parsing service). */
@Injectable({ providedIn: 'root' })
export class ExpenseInboxService {
  private expenses = inject(ExpensesService);

  #drafts = signal<EmailExpenseDraft[]>(EMAIL_DRAFTS_MOCK);
  readonly drafts = this.#drafts.asReadonly();

  getDrafts(): Observable<EmailExpenseDraft[]> {
    return simulateRequest(this.#drafts());
  }

  confirmDraft(draftId: string, edited: { providerName: string; providerRuc: string; amount: number; category: string }): Observable<void> {
    const draft = this.#drafts().find((d) => d.id === draftId);
    if (!draft) throw new Error('Borrador no encontrado.');

    this.#drafts.update((list) => list.map((d) => (d.id === draftId ? { ...d, status: 'convertido' } : d)));

    this.expenses
      .createExpense({
        date: draft.parsedDate,
        category: edited.category,
        providerName: edited.providerName,
        providerRuc: edited.providerRuc,
        amount: Math.round((edited.amount / 1.15) * 100) / 100,
        ivaAmount: Math.round((edited.amount - edited.amount / 1.15) * 100) / 100,
        total: edited.amount,
        paymentMethod: 'transferencia',
        description: `Gasto detectado automáticamente desde correo (${draft.subjectRaw}).`,
        sourceType: 'email',
      })
      .subscribe();

    return simulateRequest(undefined);
  }

  discardDraft(draftId: string): Observable<void> {
    this.#drafts.update((list) => list.map((d) => (d.id === draftId ? { ...d, status: 'descartado' } : d)));
    return simulateRequest(undefined);
  }
}
