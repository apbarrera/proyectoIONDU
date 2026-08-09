export type AiAttachmentType = 'image' | 'audio';
export type AiInputType = 'texto' | 'imagen' | 'voz';
export type AiProposalType = 'expense' | 'inventory';
export type AiInteractionResult = 'pendiente' | 'confirmado' | 'corregido' | 'cancelado';

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
}

export interface AiExpenseProposal {
  category: string;
  providerName: string;
  amount: number;
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
}
