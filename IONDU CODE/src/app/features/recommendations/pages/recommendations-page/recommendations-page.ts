import { Component, inject } from '@angular/core';
import { RecommendationsService } from '../../services/recommendations.service';
import { RecommendationPriority } from '../../models/recommendation.model';
import { PageHeader } from '../../../../shared/components/page-header/page-header';
import { EmptyState } from '../../../../shared/components/empty-state/empty-state';
import { StatusBadge, BadgeTone } from '../../../../shared/components/status-badge/status-badge';

const PRIORITY_TONES: Record<RecommendationPriority, BadgeTone> = {
  alta: 'danger',
  media: 'warning',
  baja: 'info',
};

@Component({
  selector: 'app-recommendations-page',
  imports: [PageHeader, EmptyState, StatusBadge],
  templateUrl: './recommendations-page.html',
  styleUrl: './recommendations-page.scss',
})
export class RecommendationsPage {
  recommendationsService = inject(RecommendationsService);
  priorityTones = PRIORITY_TONES;
}
