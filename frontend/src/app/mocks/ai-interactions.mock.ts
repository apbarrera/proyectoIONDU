import { AiInteraction } from '../features/ai-agent/models/ai-message.model';
import { USER_IDS } from './seed-ids.const';

export const AI_INTERACTIONS_MOCK: AiInteraction[] = [
  {
    id: 'ai-int-001',
    userId: USER_IDS.OPERATOR,
    userName: 'Juan Carlos Pérez',
    timestamp: '2026-08-06T11:05:00.000Z',
    inputType: 'texto',
    instruction: 'Compré 10 kg de azúcar por $9,50 en efectivo.',
    interpretedData: 'Gasto: Insumos — $9.50 · Proveedor no especificado',
    proposal: {
      id: 'ai-prop-001',
      type: 'expense',
      summary: 'Registrar gasto de $9.50 en la categoría Insumos.',
      expense: { category: 'Insumos', providerName: 'Proveedor no especificado', amount: 9.5 },
    },
    result: 'confirmado',
  },
];
