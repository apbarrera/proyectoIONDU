import { Injectable, computed, inject, signal } from '@angular/core';
import { Observable } from 'rxjs';
import { Expense } from '../models/expense.model';
import { EXPENSES_MOCK } from '../../../mocks/expenses.mock';
import { simulateRequest } from '../../../core/services/mock-http.util';
import { generateId } from '../../../core/utils/id.util';
import { AuditService } from '../../../core/services/audit.service';
import { AuthService } from '../../../core/services/auth.service';

export type NewExpenseInput = Omit<Expense, 'id' | 'createdBy'>;

@Injectable({ providedIn: 'root' })
export class ExpensesService {
  private audit = inject(AuditService);
  private auth = inject(AuthService);

  #expenses = signal<Expense[]>(EXPENSES_MOCK);
  readonly expenses = this.#expenses.asReadonly();

  readonly totalExpenses = computed(() => this.#expenses().reduce((sum, e) => sum + e.total, 0));

  getExpenses(): Observable<Expense[]> {
    return simulateRequest(this.#expenses());
  }

  createExpense(input: NewExpenseInput): Observable<Expense> {
    const user = this.auth.currentUser();
    const expense: Expense = { ...input, id: generateId(), createdBy: user?.fullName ?? 'Usuario' };
    this.#expenses.update((list) => [expense, ...list]);

    this.audit.log({
      userId: user?.id ?? '',
      userName: expense.createdBy,
      module: 'gastos',
      action: 'Registró gasto',
      description: `${expense.createdBy} registró un gasto de $${expense.total.toFixed(2)} en ${expense.providerName}.`,
    });

    return simulateRequest(expense);
  }

  updateExpense(id: string, changes: Partial<Expense>): Observable<Expense> {
    this.#expenses.update((list) => list.map((e) => (e.id === id ? { ...e, ...changes } : e)));
    return simulateRequest(this.#expenses().find((e) => e.id === id)!);
  }
}
