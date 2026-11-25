import { Injectable, inject } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable, map } from 'rxjs';

import { environment } from '../../../../environments/environment';
import { DateRange } from '../../../shared/utils/date-range.util';
import { DashboardSummary } from '../models/dashboard-summary.model';

interface DashboardDto extends Omit<DashboardSummary, 'topProducts' | 'inventory'> {
  from: string;
  to: string;
  topProducts: (Omit<DashboardSummary['topProducts'][number], 'productId'> & { productId: number })[];
  inventory: Omit<DashboardSummary['inventory'], 'lowStockProducts'> & {
    lowStockProducts: (Omit<DashboardSummary['inventory']['lowStockProducts'][number], 'productId'> & {
      productId: number;
    })[];
  };
}

/** Indicadores financieros calculados por el backend (`GET /api/dashboard`, solo Administrador). */
@Injectable({ providedIn: 'root' })
export class DashboardService {
  private readonly http = inject(HttpClient);

  summary(range: DateRange): Observable<DashboardSummary> {
    const params = new HttpParams().set('from', range.from).set('to', range.to);

    return this.http.get<DashboardDto>(`${environment.apiUrl}/dashboard`, { params }).pipe(
      map((dto) => ({
        income: dto.income,
        expenses: dto.expenses,
        profit: dto.profit,
        salesCount: dto.salesCount,
        expensesCount: dto.expensesCount,
        averageTicket: dto.averageTicket,
        topProducts: dto.topProducts.map((p) => ({ ...p, productId: String(p.productId) })),
        dailySeries: dto.dailySeries,
        expensesByCategory: dto.expensesByCategory,
        inventory: {
          ...dto.inventory,
          lowStockProducts: dto.inventory.lowStockProducts.map((p) => ({ ...p, productId: String(p.productId) })),
        },
      })),
    );
  }
}
