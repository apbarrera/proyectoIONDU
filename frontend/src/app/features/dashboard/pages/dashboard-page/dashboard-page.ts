import { Component, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import { DashboardService } from '../../services/dashboard.service';
import { DashboardSummary, EMPTY_DASHBOARD_SUMMARY } from '../../models/dashboard-summary.model';
import { DateRange, resolveDateRange } from '../../../../shared/utils/date-range.util';
import { PageHeader } from '../../../../shared/components/page-header/page-header';
import { PeriodSelector } from '../../../../shared/components/period-selector/period-selector';
import { Card } from '../../../../shared/components/card/card';
import { EmptyState } from '../../../../shared/components/empty-state/empty-state';
import { KpiGrid } from '../../components/kpi-grid/kpi-grid';
import { SalesChart } from '../../components/sales-chart/sales-chart';
import { Icon } from '../../../../shared/components/icon/icon';

@Component({
  selector: 'app-dashboard-page',
  imports: [RouterLink, PageHeader, PeriodSelector, Card, EmptyState, KpiGrid, SalesChart, Icon],
  templateUrl: './dashboard-page.html',
  styleUrl: './dashboard-page.scss',
})
export class DashboardPage {
  private dashboardService = inject(DashboardService);

  range = signal<DateRange>(resolveDateRange('esteMes'));
  summary = signal<DashboardSummary>(EMPTY_DASHBOARD_SUMMARY);
  loading = signal(true);

  constructor() {
    this.load();
  }

  onRangeChange(range: DateRange): void {
    this.range.set(range);
    this.load();
  }

  private load(): void {
    const range = this.range();
    this.loading.set(true);
    this.dashboardService.summary(range).subscribe({
      next: (summary) => {
        // Ignora la respuesta si el usuario ya eligió otro período mientras llegaba.
        if (this.range() !== range) return;
        this.summary.set(summary);
        this.loading.set(false);
      },
      // El interceptor ya mostró el error (por ejemplo, el dashboard es solo para el Administrador).
      error: () => this.loading.set(false),
    });
  }
}
