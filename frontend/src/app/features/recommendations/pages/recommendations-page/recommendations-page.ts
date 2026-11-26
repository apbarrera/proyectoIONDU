import { Component, inject } from '@angular/core';
import { DatePipe } from '@angular/common';
import { Button } from '../../../../shared/components/button/button';
import { Icon } from '../../../../shared/components/icon/icon';
import { AiThinking } from '../../../ai-agent/components/ai-thinking/ai-thinking';
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
  imports: [PageHeader, EmptyState, StatusBadge, Button, Icon, AiThinking, DatePipe],
  templateUrl: './recommendations-page.html',
  styleUrl: './recommendations-page.scss',
})
export class RecommendationsPage {
  recommendationsService = inject(RecommendationsService);
  priorityTones = PRIORITY_TONES;

  constructor() {
    this.recommendationsService.refresh();
  }
}
