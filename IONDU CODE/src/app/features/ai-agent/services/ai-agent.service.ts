import { Injectable, inject, signal } from '@angular/core';
import { Observable, tap } from 'rxjs';
import { AiAttachment, AiInputType, AiInteraction, AiMessage } from '../models/ai-message.model';
import { AI_INTERACTIONS_MOCK } from '../../../mocks/ai-interactions.mock';
import { simulateRequest } from '../../../core/services/mock-http.util';
import { generateId } from '../../../core/utils/id.util';
import { AiNluMockService } from './ai-nlu-mock.service';
import { TokenUsageService } from './token-usage.service';
import { ExpensesService } from '../../expenses/services/expenses.service';
import { AdjustmentsService } from '../../inventory/services/adjustments.service';
import { ProductsService } from '../../inventory/services/products.service';
import { AuditService } from '../../../core/services/audit.service';
import { AuthService } from '../../../core/services/auth.service';
import { TenantService } from '../../../core/services/tenant.service';

@Injectable({ providedIn: 'root' })
export class AiAgentService {
  private nlu = inject(AiNluMockService);
  private tokenUsage = inject(TokenUsageService);
  private expenses = inject(ExpensesService);
  private adjustments = inject(AdjustmentsService);
  private products = inject(ProductsService);
  private audit = inject(AuditService);
  private auth = inject(AuthService);
  private tenant = inject(TenantService);

  #messages = signal<AiMessage[]>([]);
  readonly messages = this.#messages.asReadonly();

  #interactions = signal<AiInteraction[]>(AI_INTERACTIONS_MOCK);
  readonly interactions = this.#interactions.asReadonly();

  send(text: string, inputType: AiInputType = 'texto', attachments?: AiAttachment[]): Observable<AiMessage> {
    const user = this.auth.currentUser();
    const userMessage: AiMessage = {
      id: generateId(),
      role: 'user',
      content: text,
      attachments,
      timestamp: new Date().toISOString(),
    };
    this.#messages.update((list) => [...list, userMessage]);
    this.tokenUsage.consume(Math.round(text.length / 3) + 40);

    const result = this.nlu.interpret(text);
    const replyContent = result.proposal
      ? `Detecté los siguientes cambios:\n\n${result.proposal.summary}\n\n¿Deseas aplicar estos cambios?`
      : result.clarifyingQuestion ?? 'No pude interpretar tu mensaje, ¿puedes darme más detalles?';

    const assistantMessage: AiMessage = {
      id: generateId(),
      role: 'assistant',
      content: replyContent,
      timestamp: new Date().toISOString(),
    };

    const interaction: AiInteraction = {
      id: generateId(),
      userId: user?.id ?? '',
      userName: user?.fullName ?? 'Usuario',
      timestamp: new Date().toISOString(),
      inputType,
      instruction: text,
      interpretedData: result.interpretedData,
      proposal: result.proposal,
      result: result.proposal ? 'pendiente' : 'cancelado',
    };
    this.#interactions.update((list) => [interaction, ...list]);

    return simulateRequest(assistantMessage, { minDelay: 500, maxDelay: 900 }).pipe(
      tap((msg) => {
        this.#messages.update((list) => [...list, msg]);
        this.tokenUsage.consume(Math.round(msg.content.length / 3));
      }),
    );
  }

  confirmProposal(
    interactionId: string,
    overrides?: { amount?: number; category?: string; quantityDelta?: number },
  ): void {
    const wasCorrected = !!overrides;
    const interaction = this.#interactions().find((i) => i.id === interactionId);
    if (!interaction?.proposal) return;
    const user = this.auth.currentUser();
    const userName = user?.fullName ?? 'Usuario';

    if (interaction.proposal.type === 'expense' && interaction.proposal.expense) {
      const expense = interaction.proposal.expense;
      const amount = overrides?.amount ?? expense.amount;
      const category = overrides?.category ?? expense.category;
      const ivaRate = this.tenant.tenant().ivaRate;
      const ivaAmount = Math.round(amount * ivaRate * 100) / 100;

      this.expenses
        .createExpense({
          date: new Date().toISOString(),
          category,
          providerName: expense.providerName,
          providerRuc: '',
          amount,
          ivaAmount,
          total: Math.round((amount + ivaAmount) * 100) / 100,
          paymentMethod: 'efectivo',
          description: `Gasto registrado por el Agente IA a partir de: "${interaction.instruction}"`,
          sourceType: 'manual',
        })
        .subscribe();
    }

    if (interaction.proposal.type === 'inventory' && interaction.proposal.inventory) {
      const inv = interaction.proposal.inventory;
      const product = this.products.getProduct(inv.productId);
      if (product) {
        const quantityDelta = overrides?.quantityDelta ?? inv.quantityDelta;
        this.adjustments.createAdjustment(inv.productId, product.currentStock + quantityDelta, 'Confirmado desde el Agente IA').subscribe();
      }
    }

    const finalResult = wasCorrected ? 'corregido' : 'confirmado';
    this.#interactions.update((list) =>
      list.map((i) => (i.id === interactionId ? { ...i, result: finalResult } : i)),
    );

    this.audit.log({
      userId: user?.id ?? '',
      userName,
      module: 'ia',
      action: 'Confirmó propuesta de IA',
      description: `${userName} confirmó una acción propuesta por el Agente IA.`,
    });
  }

  cancelProposal(interactionId: string): void {
    this.#interactions.update((list) => list.map((i) => (i.id === interactionId ? { ...i, result: 'cancelado' } : i)));
  }
}
