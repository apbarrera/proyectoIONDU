import { Component, computed, inject, input, output, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { AiInteraction } from '../../models/ai-message.model';
import { AiAgentService } from '../../services/ai-agent.service';
import { Button } from '../../../../shared/components/button/button';
import { StatusBadge, BadgeTone } from '../../../../shared/components/status-badge/status-badge';

const RESULT_LABELS: Record<AiInteraction['result'], string> = {
  pendiente: 'Esperando confirmación',
  confirmado: 'Confirmado',
  corregido: 'Corregido',
  cancelado: 'Cancelado',
};

const RESULT_TONES: Record<AiInteraction['result'], BadgeTone> = {
  pendiente: 'warning',
  confirmado: 'success',
  corregido: 'info',
  cancelado: 'neutral',
};

@Component({
  selector: 'app-proposal-card',
  imports: [FormsModule, Button, StatusBadge],
  templateUrl: './proposal-card.html',
  styleUrl: './proposal-card.scss',
})
export class ProposalCard {
  private aiAgent = inject(AiAgentService);

  interaction = input.required<AiInteraction>();
  resolved = output<void>();

  resultLabels = RESULT_LABELS;
  resultTones = RESULT_TONES;

  editing = signal(false);
  editedAmount = signal(0);
  editedCategory = signal('');
  editedQuantity = signal(0);

  isPending = computed(() => this.interaction().result === 'pendiente');

  startEdit(): void {
    const proposal = this.interaction().proposal;
    if (!proposal) return;
    if (proposal.expense) {
      this.editedAmount.set(proposal.expense.amount);
      this.editedCategory.set(proposal.expense.category);
    }
    if (proposal.inventory) {
      this.editedQuantity.set(proposal.inventory.quantityDelta);
    }
    this.editing.set(true);
  }

  confirm(): void {
    const overrides = this.editing()
      ? {
          amount: this.editedAmount(),
          category: this.editedCategory(),
          quantityDelta: this.editedQuantity(),
        }
      : undefined;
    this.aiAgent.confirmProposal(this.interaction().id, overrides);
    this.editing.set(false);
    this.resolved.emit();
  }

  cancel(): void {
    this.aiAgent.cancelProposal(this.interaction().id);
    this.editing.set(false);
    this.resolved.emit();
  }
}
