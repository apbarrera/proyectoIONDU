import { HttpClient } from '@angular/common/http';
import { Injectable, inject, signal } from '@angular/core';
import { Observable, catchError, defer, finalize, map, of, tap } from 'rxjs';
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
  AiInventoryProposal,
} from '../models/ai-message.model';

interface AiProposalDto {
  type: 'expense' | 'inventory';
  summary: string;
  inventory?: AiInventoryProposal;
  expense?: {
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
  /** Solo en mensajes de voz: lo que se entendió del audio. */
  transcript?: string | null;
}

const AUDIO_EXTENSIONS: Record<string, string> = { webm: 'webm', ogg: 'ogg', mp4: 'm4a', mpeg: 'mp3', wav: 'wav' };

interface AiActionDto {
  id: number;
  timestamp: string;
  userName: string;
  instruction: string;
  reply: string;
  proposal: AiProposalDto | null;
  status: AiInteractionResult;
  expenseId: number | null;
  movementId: number | null;
  inputType?: AiInputType;
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

  /** Qué está procesando el agente ahora (null si nada): lo muestran el chat y el panel. */
  #thinking = signal<AiInputType | null>(null);
  readonly thinking = this.#thinking.asReadonly();

  send(text: string, inputType: AiInputType = 'texto', attachments?: AiAttachment[]): Observable<AiMessage> {
    this.#messages.update((list) => [
      ...list,
      { id: generateId(), role: 'user', content: text, attachments, timestamp: new Date().toISOString() },
    ]);

    return this.#handleReply(this.http.post<AiReplyDto>(`${this.baseUrl}/messages`, { text }), () => text, inputType);
  }

  /**
   * Envía un mensaje de voz (RF-6.4). El servidor lo transcribe y lo interpreta como texto;
   * la burbuja del usuario muestra luego lo que se entendió. El audio no se guarda.
   */
  sendAudio(audio: Blob): Observable<AiMessage> {
    const messageId = generateId();
    this.#messages.update((list) => [
      ...list,
      { id: messageId, role: 'user', content: '🎙️ Mensaje de voz', timestamp: new Date().toISOString() },
    ]);

    const subtype = audio.type.split(';')[0].split('/')[1] ?? 'webm';
    const form = new FormData();
    form.append('audio', audio, `mensaje.${AUDIO_EXTENSIONS[subtype] ?? 'webm'}`);
    const request = this.http.post<AiReplyDto>(`${this.baseUrl}/audio`, form).pipe(
      tap((dto) => {
        if (dto.transcript) {
          const transcript = dto.transcript;
          this.#messages.update((list) =>
            list.map((m) => (m.id === messageId ? { ...m, content: `🎙️ «${transcript}»` } : m)),
          );
        }
      }),
    );
    return this.#handleReply(request, (dto) => `[Voz] ${dto.transcript ?? ''}`.trim(), 'voz');
  }

  /** Aviso del asistente que no pasa por el servidor (p. ej., sin permiso de micrófono). */
  notify(content: string): void {
    this.#reply(content);
  }

  /**
   * Envía la foto de una factura, ticket o guía (RF-6.3). `caption` es el texto opcional
   * que la acompaña. El servidor la reduce y no la guarda.
   */
  sendImage(file: File, caption = ''): Observable<AiMessage> {
    const text = caption.trim();
    this.#messages.update((list) => [
      ...list,
      {
        id: generateId(),
        role: 'user',
        content: text || file.name,
        attachments: [{ type: 'image', url: URL.createObjectURL(file), name: file.name }],
        timestamp: new Date().toISOString(),
      },
    ]);

    const form = new FormData();
    form.append('image', file, file.name);
    if (text) form.append('text', text);
    const instruction = text ? `[Imagen] ${text}` : '[Imagen]';
    return this.#handleReply(this.http.post<AiReplyDto>(`${this.baseUrl}/images`, form), () => instruction, 'imagen');
  }

  #handleReply(
    request: Observable<AiReplyDto>,
    instructionFor: (dto: AiReplyDto) => string,
    inputType: AiInputType,
  ): Observable<AiMessage> {
    const reply = request.pipe(
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
            instruction: instructionFor(dto),
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
    return defer(() => {
      this.#thinking.set(inputType);
      return reply;
    }).pipe(finalize(() => this.#thinking.set(null)));
  }

  /** Confirma la propuesta; con `corrections`, queda como "corregida" (RF-6.10). */
  confirmProposal(interactionId: string, corrections?: AiProposalCorrections): void {
    const body: Record<string, number> = {};
    if (corrections?.amount !== undefined) body['total'] = corrections.amount;
    if (corrections?.categoryId !== undefined) body['categoryId'] = corrections.categoryId;
    if (corrections?.quantity !== undefined) body['quantity'] = corrections.quantity;

    this.http
      .post<{ status: AiInteractionResult; expenseId: number | null; movementId: number | null }>(
        `${this.baseUrl}/actions/${interactionId}/confirm`,
        body,
      )
      .subscribe((result) => this.#setResult(interactionId, result.status, result.expenseId, result.movementId));
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
          inputType: dto.inputType ?? 'texto',
          instruction: dto.instruction,
          interpretedData: dto.proposal?.summary ?? dto.reply,
          proposal: dto.proposal ? toProposal(String(dto.id), dto.proposal) : null,
          result: dto.status,
          expenseId: dto.expenseId,
          movementId: dto.movementId,
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

  #setResult(
    interactionId: string,
    result: AiInteractionResult,
    expenseId?: number | null,
    movementId?: number | null,
  ): void {
    this.#interactions.update((list) =>
      list.map((i) =>
        i.id === interactionId
          ? { ...i, result, expenseId: expenseId ?? i.expenseId, movementId: movementId ?? i.movementId }
          : i,
      ),
    );
  }
}

function toProposal(id: string, dto: AiProposalDto): AiProposal {
  if (dto.type === 'inventory' && dto.inventory) {
    return { id, type: 'inventory', summary: dto.summary, inventory: dto.inventory };
  }
  const expense = dto.expense!;
  return {
    id,
    type: 'expense',
    summary: dto.summary,
    expense: {
      amount: expense.total,
      ivaAmount: expense.ivaAmount,
      categoryId: expense.categoryId,
      category: expense.categoryName,
      description: expense.description,
      providerName: expense.supplierName,
      paymentMethod: expense.paymentMethod,
      date: expense.date,
    },
  };
}
