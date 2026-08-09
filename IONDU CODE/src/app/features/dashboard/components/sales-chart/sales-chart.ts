import { Component, computed, input } from '@angular/core';
import { DailyPoint } from '../../models/dashboard-summary.model';

@Component({
  selector: 'app-sales-chart',
  imports: [],
  templateUrl: './sales-chart.html',
  styleUrl: './sales-chart.scss',
})
export class SalesChart {
  series = input.required<DailyPoint[]>();

  maxIncome = computed(() => Math.max(1, ...this.series().map((p) => p.income)));

  barHeight(point: DailyPoint): number {
    return Math.max(4, Math.round((point.income / this.maxIncome()) * 100));
  }

  shortDate(date: string): string {
    return new Date(`${date}T00:00:00`).toLocaleDateString('es-EC', { day: '2-digit', month: 'short' });
  }
}
