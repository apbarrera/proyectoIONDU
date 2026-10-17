import { Injectable, inject } from '@angular/core';
import { DateRange } from '../../../shared/utils/date-range.util';
import { SalesService } from '../../sales/services/sales.service';
import { ExpensesService } from '../../expenses/services/expenses.service';
import { DailyPoint, DashboardSummary, TopProduct } from '../models/dashboard-summary.model';

/** Pure read-only aggregator over other domains' signals — never mutates anything. */
@Injectable({ providedIn: 'root' })
export class DashboardService {
  private sales = inject(SalesService);
  private expenses = inject(ExpensesService);

  summary(range: DateRange): DashboardSummary {
    const from = new Date(`${range.from}T00:00:00`).getTime();
    const to = new Date(`${range.to}T23:59:59`).getTime();

    const salesInRange = this.sales
      .sales()
      .filter((s) => s.status === 'completada')
      .filter((s) => {
        const t = new Date(s.date).getTime();
        return t >= from && t <= to;
      });

    const expensesInRange = this.expenses.expenses().filter((e) => {
      const t = new Date(e.date).getTime();
      return t >= from && t <= to;
    });

    const income = round(salesInRange.reduce((sum, s) => sum + s.total, 0));
    const expensesTotal = round(expensesInRange.reduce((sum, e) => sum + e.total, 0));

    const productTotals = new Map<string, TopProduct>();
    salesInRange.forEach((sale) => {
      sale.items.forEach((item) => {
        const existing = productTotals.get(item.productId);
        if (existing) {
          existing.unitsSold += item.quantity;
          existing.revenue = round(existing.revenue + item.subtotal);
        } else {
          productTotals.set(item.productId, {
            productId: item.productId,
            name: item.productName,
            unitsSold: item.quantity,
            revenue: item.subtotal,
          });
        }
      });
    });

    const dailyMap = new Map<string, number>();
    salesInRange.forEach((sale) => {
      const day = sale.date.slice(0, 10);
      dailyMap.set(day, round((dailyMap.get(day) ?? 0) + sale.total));
    });
    const dailySeries: DailyPoint[] = Array.from(dailyMap.entries())
      .sort(([a], [b]) => a.localeCompare(b))
      .map(([date, incomeForDay]) => ({ date, income: incomeForDay }));

    return {
      income,
      expenses: expensesTotal,
      profit: round(income - expensesTotal),
      salesCount: salesInRange.length,
      averageTicket: salesInRange.length ? round(income / salesInRange.length) : 0,
      topProducts: Array.from(productTotals.values())
        .sort((a, b) => b.revenue - a.revenue)
        .slice(0, 5),
      dailySeries,
    };
  }
}

function round(value: number): number {
  return Math.round(value * 100) / 100;
}
