import { Component, computed, input } from '@angular/core';
import { DailyPoint } from '../../models/dashboard-summary.model';

const MAX_LABELS = 8;
const EMPTY_SCALE = 100;

@Component({
  selector: 'app-sales-chart',
  imports: [],
  templateUrl: './sales-chart.html',
  styleUrl: './sales-chart.scss',
})
export class SalesChart {
  series = input.required<DailyPoint[]>();

  /** Tope del eje redondeado a 1, 2, 5 o 10 × una potencia de 10, para que las líneas guía sean legibles. */
  niceMax = computed(() => {
    const max = Math.max(...this.series().map((p) => p.income), 0);
    if (max === 0) return EMPTY_SCALE;
    const magnitude = 10 ** Math.floor(Math.log10(max));
    const ratio = max / magnitude;
    const step = ratio <= 1 ? 1 : ratio <= 2 ? 2 : ratio <= 5 ? 5 : 10;
    return step * magnitude;
  });

  ticks = computed(() => [1, 0.75, 0.5, 0.25, 0].map((fraction) => this.niceMax() * fraction));

  /** Con muchos días se muestra una etiqueta de cada N para que no se encimen. */
  private labelEvery = computed(() => Math.max(1, Math.ceil(this.series().length / MAX_LABELS)));

  barHeight(point: DailyPoint): number {
    return Math.max(2, (point.income / this.niceMax()) * 100);
  }

  showLabel(index: number): boolean {
    return index % this.labelEvery() === 0;
  }

  money(value: number): string {
    return `$${value.toLocaleString('en-US', { maximumFractionDigits: 2 })}`;
  }

  shortDate(date: string): string {
    return new Date(`${date}T00:00:00`).toLocaleDateString('es-EC', { day: '2-digit', month: 'short' });
  }

  summaryLabel = computed(() => {
    const total = this.series().reduce((sum, p) => sum + p.income, 0);
    return `Ingresos de ${this.series().length} días, total ${this.money(total)}`;
  });
}
