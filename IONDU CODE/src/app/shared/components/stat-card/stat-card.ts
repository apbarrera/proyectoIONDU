import { Component, input } from '@angular/core';

export type StatTrend = 'up' | 'down' | 'neutral';

@Component({
  selector: 'app-stat-card',
  imports: [],
  templateUrl: './stat-card.html',
  styleUrl: './stat-card.scss',
})
export class StatCard {
  label = input.required<string>();
  value = input.required<string>();
  trendLabel = input<string>();
  trend = input<StatTrend>('neutral');
  icon = input<string>();
}
