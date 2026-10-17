import { Component, input } from '@angular/core';
import { Icon } from '../icon/icon';
import { IconName } from '../../icons/icons.generated';

export type StatTrend = 'up' | 'down' | 'neutral';

@Component({
  selector: 'app-stat-card',
  imports: [Icon],
  templateUrl: './stat-card.html',
  styleUrl: './stat-card.scss',
})
export class StatCard {
  label = input.required<string>();
  value = input.required<string>();
  trendLabel = input<string>();
  trend = input<StatTrend>('neutral');
  icon = input<IconName>();
}
