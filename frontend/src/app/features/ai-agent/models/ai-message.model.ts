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

/** Movimiento de inventario que propone el agente. En un ajuste, `quantity` es el stock contado. */
export interface AiInventoryProposal {
  productId: number;
  productName: string;
  type: 'entrada' | 'salida' | 'ajuste';
  quantity: number;
  unit: string;
  currentStock: number;
  resultingStock: number;
  reason: string;
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
  movementId?: number | null;
}

/** Correcciones antes de confirmar (botón "Corregir"). */
export interface AiProposalCorrections {
  amount?: number;
  categoryId?: number;
  /** Inventario: cantidad (o stock contado en un ajuste). */
  quantity?: number;
}
