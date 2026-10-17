import { Component, inject } from '@angular/core';
import { RouterLink } from '@angular/router';
import { ProductsService } from '../../services/products.service';
import { PageHeader } from '../../../../shared/components/page-header/page-header';
import { EmptyState } from '../../../../shared/components/empty-state/empty-state';
import { StatusBadge } from '../../../../shared/components/status-badge/status-badge';
import { Icon } from '../../../../shared/components/icon/icon';

@Component({
  selector: 'app-alerts',
  imports: [RouterLink, PageHeader, EmptyState, StatusBadge, Icon],
  templateUrl: './alerts.html',
  styleUrl: './alerts.scss',
})
export class Alerts {
  productsService = inject(ProductsService);

  severity(currentStock: number, minStock: number): 'danger' | 'warning' {
    return currentStock <= 0 ? 'danger' : currentStock <= minStock * 0.5 ? 'danger' : 'warning';
  }

  severityLabel(currentStock: number, minStock: number): string {
    if (currentStock <= 0) return 'Agotado';
    return this.severity(currentStock, minStock) === 'danger' ? 'Crítico' : 'Bajo';
  }
}
