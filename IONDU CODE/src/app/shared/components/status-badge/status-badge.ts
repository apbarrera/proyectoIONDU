import { Component, input } from '@angular/core';

export type BadgeTone = 'success' | 'warning' | 'danger' | 'info' | 'neutral';

@Component({
  selector: 'app-status-badge',
  imports: [],
  templateUrl: './status-badge.html',
  styleUrl: './status-badge.scss',
})
export class StatusBadge {
  label = input.required<string>();
  tone = input<BadgeTone>('neutral');
}
