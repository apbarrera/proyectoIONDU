import { Component, computed, inject, input, output, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { AiInteraction, AiProposalCorrections } from '../../models/ai-message.model';
import { AiAgentService } from '../../services/ai-agent.service';
import { ExpensesService } from '../../../expenses/services/expenses.service';
import { Button } from '../../../../shared/components/button/button';
import { StatusBadge, BadgeTone } from '../../../../shared/components/status-badge/status-badge';

const RESULT_LABELS: Record<AiInteraction['result'], string> = {
  pendiente: 'Esperando confirmación',
  confirmado: 'Confirmado',
  corregido: 'Corregido',
  cancelado: 'Cancelado',
  sin_propuesta: 'Sin propuesta',
};

const RESULT_TONES: Record<AiInteraction['result'], BadgeTone> = {
  pendiente: 'warning',
  confirmado: 'success',
  corregido: 'info',
  cancelado: 'neutral',
  sin_propuesta: 'neutral',
};

@Component({
  selector: 'app-proposal-card',
  imports: [FormsModule, Button, StatusBadge],
  templateUrl: './proposal-card.html',
  styleUrl: './proposal-card.scss',
})
export class ProposalCard {
  private aiAgent = inject(AiAgentService);
  readonly expenses = inject(ExpensesService);

  interaction = input.required<AiInteraction>();
  resolved = output<void>();

  resultLabels = RESULT_LABELS;
  resultTones = RESULT_TONES;

  editing = signal(false);
  editedAmount = signal(0);
  editedCategoryId = signal(0);
  editedQuantity = signal(0);

  isPending = computed(() => this.interaction().result === 'pendiente');

  startEdit(): void {
    const proposal = this.interaction().proposal;
    if (!proposal) return;
    if (proposal.expense) {
      this.editedAmount.set(proposal.expense.amount);
      this.editedCategoryId.set(proposal.expense.categoryId);
      if (!this.expenses.categories().length) this.expenses.loadCategories().subscribe();
    }
    if (proposal.inventory) {
      this.editedQuantity.set(proposal.inventory.quantity);
    }
    this.editing.set(true);
  }

  confirm(): void {
    const { expense, inventory } = this.interaction().proposal ?? {};
    let corrections: AiProposalCorrections | undefined;
    if (this.editing() && expense) {
      corrections = {
        ...(this.editedAmount() !== expense.amount ? { amount: this.editedAmount() } : {}),
        ...(this.editedCategoryId() !== expense.categoryId ? { categoryId: this.editedCategoryId() } : {}),
      };
    } else if (this.editing() && inventory && this.editedQuantity() !== inventory.quantity) {
      corrections = { quantity: this.editedQuantity() };
    }
    this.aiAgent.confirmProposal(this.interaction().id, corrections);
    this.editing.set(false);
    this.resolved.emit();
  }

  cancel(): void {
    this.aiAgent.cancelProposal(this.interaction().id);
    this.editing.set(false);
    this.resolved.emit();
  }
}
