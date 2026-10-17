import { Component, input } from '@angular/core';
import { DashboardSummary } from '../../models/dashboard-summary.model';
import { StatCard } from '../../../../shared/components/stat-card/stat-card';

@Component({
  selector: 'app-kpi-grid',
  imports: [StatCard],
  templateUrl: './kpi-grid.html',
  styleUrl: './kpi-grid.scss',
})
export class KpiGrid {
  summary = input.required<DashboardSummary>();
}
