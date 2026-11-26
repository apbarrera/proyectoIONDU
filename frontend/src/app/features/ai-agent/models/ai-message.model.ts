export type AiAttachmentType = 'image' | 'audio';
export type AiInputType = 'texto' | 'imagen' | 'voz';
export type AiProposalType = 'expense' | 'inventory';
export type AiInteractionResult = 'pendiente' | 'confirmado' | 'corregido' | 'cancelado' | 'sin_propuesta';

export interface AiAttachment {
  type: AiAttachmentType;
  url: string;
  name: string;
}

export interface AiMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  attachments?: AiAttachment[];
  timestamp: string;
  /** Propuesta asociada a la respuesta del asistente, si la hay. */
  interactionId?: string;
}

/** Gasto que propone el agente (lo valida y lo guarda el backend al confirmar). */
export interface AiExpenseProposal {
  amount: number;
  ivaAmount: number;
  categoryId: number;
  category: string;
  description: string;
  providerName: string | null;
  paymentMethod: string;
  date: string | null;
}

export interface AiInventoryProposal {
  productId: string;
  productName: string;
  quantityDelta: number;
  unit: string;
}

export interface AiProposal {
  id: string;
  type: AiProposalType;
  summary: string;
  expense?: AiExpenseProposal;
  inventory?: AiInventoryProposal;
}

export interface AiInteraction {
  id: string;
  userId: string;
  userName: string;
  timestamp: string;
  inputType: AiInputType;
  instruction: string;
  interpretedData: string;
  proposal: AiProposal | null;
  result: AiInteractionResult;
  expenseId?: number | null;
}

/** Correcciones antes de confirmar (botón "Corregir"). */
export interface AiProposalCorrections {
  amount?: number;
  categoryId?: number;
}
