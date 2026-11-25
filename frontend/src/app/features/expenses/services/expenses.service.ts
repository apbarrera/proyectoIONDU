import { Injectable, computed, inject, signal } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable, map, of, switchMap, tap } from 'rxjs';

import { environment } from '../../../../environments/environment';
import { fetchAllPages } from '../../../core/utils/pagination.util';
import {
  Expense,
  ExpenseCategory,
  ExpensePaymentMethod,
  ExpenseSourceType,
  ExpenseStatus,
  Supplier,
} from '../models/expense.model';
import { SuppliersApiService } from './suppliers-api.service';

interface ExpenseDto {
  id: number;
  date: string;
  categoryId: number;
  categoryName: string;
  supplierId: number | null;
  supplierName: string | null;
  supplierIdentification: string | null;
  total: number;
  description: string;
  paymentMethod: ExpensePaymentMethod;
  receiptNumber: string | null;
  status: ExpenseStatus;
  source: 'manual' | 'correo';
}

/** Datos para registrar un gasto. La categoría se da por nombre y el proveedor por RUC/cédula y nombre. */
export interface NewExpenseInput {
  date: string;
  category: string;
  providerName: string;
  providerRuc: string;
  total: number;
  paymentMethod: ExpensePaymentMethod;
  description: string;
  receiptNumber?: string;
}

/** Datos del formulario de edición; la fecha es `AAAA-MM-DD` y el proveedor va por RUC o cédula. */
export interface EditExpenseInput {
  date: string;
  categoryId: number;
  providerRuc: string;
  providerName: string;
  total: number;
  paymentMethod: ExpensePaymentMethod;
  description: string;
  receiptNumber: string;
}

/** Fecha del gasto en Ecuador como `AAAA-MM-DD` (para el campo `<input type="date">`). */
export function expenseDay(iso: string): string {
  return new Date(iso).toLocaleDateString('en-CA', { timeZone: 'America/Guayaquil' });
}

/** Categoría a la que van los gastos cuya categoría no existe (una de las 7 predefinidas del backend). */
const FALLBACK_CATEGORY = 'Otros gastos operativos';

function toExpense(dto: ExpenseDto): Expense {
  const source: ExpenseSourceType = dto.source === 'correo' ? 'email' : 'manual';
  return {
    id: String(dto.id),
    date: dto.date,
    categoryId: dto.categoryId,
    category: dto.categoryName,
    supplierId: dto.supplierId,
    providerName: dto.supplierName ?? '',
    providerRuc: dto.supplierIdentification ?? '',
    total: dto.total,
    paymentMethod: dto.paymentMethod,
    description: dto.description,
    receiptNumber: dto.receiptNumber ?? undefined,
    sourceType: source,
    status: dto.status,
  };
}

/** Gastos, categorías de gasto y proveedores (`/api/expenses`, `/api/expense-categories`). */
@Injectable({ providedIn: 'root' })
export class ExpensesService {
  private readonly http = inject(HttpClient);
  private readonly suppliers = inject(SuppliersApiService);
  private readonly expensesUrl = `${environment.apiUrl}/expenses`;
  private readonly categoriesUrl = `${environment.apiUrl}/expense-categories`;

  #expenses = signal<Expense[]>([]);
  readonly expenses = this.#expenses.asReadonly();

  #categories = signal<ExpenseCategory[]>([]);
  readonly categories = this.#categories.asReadonly();

  readonly totalExpenses = computed(() =>
    this.#expenses()
      .filter((e) => e.status !== 'anulado')
      .reduce((sum, e) => sum + e.total, 0),
  );

  /** Descarga todos los gastos (el más reciente primero) y actualiza `expenses`. */
  getExpenses(): Observable<Expense[]> {
    return fetchAllPages<ExpenseDto>((page) =>
      this.http.get<{ items: ExpenseDto[]; total: number; page: number; pageSize: number }>(this.expensesUrl, {
        params: new HttpParams().set('page', page).set('pageSize', 100),
      }),
    ).pipe(
      map((items) => items.map(toExpense)),
      tap((expenses) => this.#expenses.set(expenses)),
    );
  }

  /**
   * Edita un gasto enviando solo los campos que cambiaron. Si cambia el RUC o la cédula del
   * proveedor, lo busca o lo crea antes; sin RUC, el gasto queda sin proveedor.
   * Devuelve `null` si no había nada que cambiar.
   */
  updateExpense(current: Expense, edit: EditExpenseInput): Observable<Expense | null> {
    const changes: Record<string, unknown> = {};
    if (edit.date !== expenseDay(current.date)) changes['date'] = `${edit.date}T12:00:00`;
    if (edit.categoryId !== current.categoryId) changes['categoryId'] = edit.categoryId;
    if (edit.total !== current.total) changes['total'] = edit.total;
    if (edit.paymentMethod !== current.paymentMethod) changes['paymentMethod'] = edit.paymentMethod;
    if (edit.description.trim() !== current.description) changes['description'] = edit.description.trim();
    const receipt = edit.receiptNumber.trim() || null;
    if (receipt !== (current.receiptNumber ?? null)) changes['receiptNumber'] = receipt;

    const ruc = edit.providerRuc.trim();
    const supplier$: Observable<Supplier | null | undefined> =
      ruc === current.providerRuc
        ? of(undefined) // sin cambios de proveedor
        : ruc
          ? this.suppliers.findOrCreate({ identification: ruc, name: edit.providerName.trim() })
          : of(null);

    return supplier$.pipe(
      switchMap((supplier) => {
        if (supplier !== undefined) changes['supplierId'] = supplier?.id ?? null;
        if (!Object.keys(changes).length) return of(null);
        return this.http
          .patch<ExpenseDto>(`${this.expensesUrl}/${encodeURIComponent(current.id)}`, changes)
          .pipe(
            map(toExpense),
            tap((expense) => this.#expenses.update((list) => list.map((e) => (e.id === expense.id ? expense : e)))),
          );
      }),
    );
  }

  /** Anula el gasto (solo Administrador): queda en el historial como `anulado`, con el motivo. */
  voidExpense(id: string, reason: string): Observable<Expense> {
    return this.http
      .post<ExpenseDto>(`${this.expensesUrl}/${encodeURIComponent(id)}/void`, { reason: reason.trim() })
      .pipe(
        map(toExpense),
        tap((expense) => this.#expenses.update((list) => list.map((e) => (e.id === expense.id ? expense : e)))),
      );
  }

  /** Categorías de la empresa; la primera vez el backend crea las 7 predefinidas. */
  loadCategories(): Observable<ExpenseCategory[]> {
    return this.http.get<ExpenseCategory[]>(this.categoriesUrl).pipe(tap((list) => this.#categories.set(list)));
  }

  createCategory(name: string): Observable<ExpenseCategory> {
    return this.http
      .post<ExpenseCategory>(this.categoriesUrl, { name: name.trim() })
      .pipe(tap((category) => this.#categories.update((list) => [...list, category])));
  }

  /**
   * Registra el gasto. Resuelve la categoría por nombre y, si trae RUC o cédula del proveedor,
   * lo busca o lo crea antes de guardar el gasto.
   */
  createExpense(input: NewExpenseInput): Observable<Expense> {
    const categories$ = this.#categories().length ? of(this.#categories()) : this.loadCategories();

    return categories$.pipe(
      switchMap((categories) => {
        const wanted = input.category.trim().toLowerCase();
        const category =
          categories.find((c) => c.name.toLowerCase() === wanted) ??
          categories.find((c) => c.name === FALLBACK_CATEGORY) ??
          categories[0];

        const ruc = input.providerRuc.trim();
        const supplier$: Observable<Supplier | null> = ruc
          ? this.suppliers.findOrCreate({ identification: ruc, name: input.providerName.trim() })
          : of(null);

        return supplier$.pipe(
          switchMap((supplier) =>
            this.http.post<ExpenseDto>(this.expensesUrl, {
              categoryId: category.id,
              supplierId: supplier?.id ?? null,
              total: input.total,
              description: input.description.trim(),
              paymentMethod: input.paymentMethod,
              date: input.date,
              receiptNumber: input.receiptNumber?.trim() || null,
            }),
          ),
        );
      }),
      map(toExpense),
      tap((expense) => this.#expenses.update((list) => [expense, ...list])),
    );
  }
}
