import { Component, computed, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import { DashboardService } from '../../services/dashboard.service';
import { ProductsService } from '../../../inventory/services/products.service';
import { DateRange, resolveDateRange } from '../../../../shared/utils/date-range.util';
import { PageHeader } from '../../../../shared/components/page-header/page-header';
import { PeriodSelector } from '../../../../shared/components/period-selector/period-selector';
import { Card } from '../../../../shared/components/card/card';
import { EmptyState } from '../../../../shared/components/empty-state/empty-state';
import { KpiGrid } from '../../components/kpi-grid/kpi-grid';
import { SalesChart } from '../../components/sales-chart/sales-chart';

@Component({
  selector: 'app-dashboard-page',
  imports: [RouterLink, PageHeader, PeriodSelector, Card, EmptyState, KpiGrid, SalesChart],
  templateUrl: './dashboard-page.html',
  styleUrl: './dashboard-page.scss',
})
export class DashboardPage {
  private dashboardService = inject(DashboardService);
  productsService = inject(ProductsService);

  range = signal<DateRange>(resolveDateRange('esteMes'));
  summary = computed(() => this.dashboardService.summary(this.range()));

  onRangeChange(range: DateRange): void {
    this.range.set(range);
  }
}
