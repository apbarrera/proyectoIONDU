import { HttpClient } from '@angular/common/http';
import { Injectable, inject, signal } from '@angular/core';
import { Observable, catchError, map, of, tap } from 'rxjs';
import { environment } from '../../../../environments/environment';
import { AuthService } from '../../../core/services/auth.service';
import { apiErrorMessage } from '../../../core/utils/api-error.util';
import { generateId } from '../../../core/utils/id.util';
import { PageDto } from '../../../core/utils/pagination.util';
import {
  AiAttachment,
  AiInputType,
  AiInteraction,
  AiInteractionResult,
  AiMessage,
  AiProposal,
  AiProposalCorrections,
} from '../models/ai-message.model';

interface AiProposalDto {
  type: 'expense';
  summary: string;
  expense: {
    total: number;
    ivaAmount: number;
    categoryId: number;
    categoryName: string;
    description: string;
    supplierName: string | null;
    paymentMethod: string;
    date: string | null;
  };
}

interface AiReplyDto {
  actionId: number | null;
  reply: string;
  proposal: AiProposalDto | null;
}

interface AiActionDto {
  id: number;
  timestamp: string;
  userName: string;
  instruction: string;
  reply: string;
  proposal: AiProposalDto | null;
  status: AiInteractionResult;
  expenseId: number | null;
}

/**
 * Agente de IA (/api/ai). El backend interpreta el mensaje con el modelo, guarda la
 * propuesta y la ejecuta solo cuando el usuario la confirma (RF-6.9).
 */
@Injectable({ providedIn: 'root' })
export class AiAgentService {
  private readonly http = inject(HttpClient);
  private readonly auth = inject(AuthService);
  private readonly baseUrl = `${environment.apiUrl}/ai`;

  #messages = signal<AiMessage[]>([]);
  readonly messages = this.#messages.asReadonly();

  #interactions = signal<AiInteraction[]>([]);
  readonly interactions = this.#interactions.asReadonly();

  send(text: string, inputType: AiInputType = 'texto', attachments?: AiAttachment[]): Observable<AiMessage> {
    this.#messages.update((list) => [
      ...list,
      { id: generateId(), role: 'user', content: text, attachments, timestamp: new Date().toISOString() },
    ]);

    if (inputType !== 'texto') {
      return of(
        this.#reply(
          'Por ahora el agente entiende solo texto. Escribe el gasto, por ejemplo: "Gasté $25 en empaques".',
        ),
      );
    }

    return this.http.post<AiReplyDto>(`${this.baseUrl}/messages`, { text }).pipe(
      map((dto) => {
        let interactionId: string | undefined;
        if (dto.actionId !== null && dto.proposal) {
          const user = this.auth.currentUser();
          const interaction: AiInteraction = {
            id: String(dto.actionId),
            userId: user?.id ?? '',
            userName: user?.fullName ?? 'Usuario',
            timestamp: new Date().toISOString(),
            inputType,
            instruction: text,
            interpretedData: dto.proposal.summary,
            proposal: toProposal(String(dto.actionId), dto.proposal),
            result: 'pendiente',
          };
          this.#interactions.update((list) => [interaction, ...list]);
          interactionId = interaction.id;
        }
        return this.#reply(dto.reply, interactionId);
      }),
      catchError((error: unknown) => of(this.#reply(apiErrorMessage(error)))),
    );
  }

  /** Confirma la propuesta; con `corrections`, queda como "corregida" (RF-6.10). */
  confirmProposal(interactionId: string, corrections?: AiProposalCorrections): void {
    const body: Record<string, number> = {};
    if (corrections?.amount !== undefined) body['total'] = corrections.amount;
    if (corrections?.categoryId !== undefined) body['categoryId'] = corrections.categoryId;

    this.http
      .post<{ status: AiInteractionResult; expenseId: number }>(
        `${this.baseUrl}/actions/${interactionId}/confirm`,
        body,
      )
      .subscribe((result) => this.#setResult(interactionId, result.status, result.expenseId));
  }

  cancelProposal(interactionId: string): void {
    this.http
      .post<void>(`${this.baseUrl}/actions/${interactionId}/cancel`, null)
      .subscribe(() => this.#setResult(interactionId, 'cancelado'));
  }

  /** Historial de la empresa (RF-6.13), del más reciente al más antiguo. */
  loadHistory(): Observable<AiInteraction[]> {
    return this.http.get<PageDto<AiActionDto>>(`${this.baseUrl}/actions`, { params: { pageSize: 100 } }).pipe(
      map((page) =>
        page.items.map((dto) => ({
          id: String(dto.id),
          userId: '',
          userName: dto.userName,
          timestamp: dto.timestamp,
          inputType: 'texto' as AiInputType,
          instruction: dto.instruction,
          interpretedData: dto.proposal?.summary ?? dto.reply,
          proposal: dto.proposal ? toProposal(String(dto.id), dto.proposal) : null,
          result: dto.status,
          expenseId: dto.expenseId,
        })),
      ),
      tap((list) => this.#interactions.set(list)),
    );
  }

  #reply(content: string, interactionId?: string): AiMessage {
    const message: AiMessage = {
      id: generateId(),
      role: 'assistant',
      content,
      timestamp: new Date().toISOString(),
      interactionId,
    };
    this.#messages.update((list) => [...list, message]);
    return message;
  }

  #setResult(interactionId: string, result: AiInteractionResult, expenseId?: number): void {
    this.#interactions.update((list) =>
      list.map((i) => (i.id === interactionId ? { ...i, result, expenseId: expenseId ?? i.expenseId } : i)),
    );
  }
}

function toProposal(id: string, dto: AiProposalDto): AiProposal {
  return {
    id,
    type: 'expense',
    summary: dto.summary,
    expense: {
      amount: dto.expense.total,
      ivaAmount: dto.expense.ivaAmount,
      categoryId: dto.expense.categoryId,
      category: dto.expense.categoryName,
      description: dto.expense.description,
      providerName: dto.expense.supplierName,
      paymentMethod: dto.expense.paymentMethod,
      date: dto.expense.date,
    },
  };
}
