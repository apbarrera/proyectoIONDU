import { EmailExpenseDraft } from '../features/expenses/models/email-draft.model';

export const EMAIL_DRAFTS_MOCK: EmailExpenseDraft[] = [
  {
    id: 'draft-001',
    receivedAt: '2026-08-08T08:15:00.000Z',
    fromAddress: 'facturacion@distribuidoraxyz.com.ec',
    subjectRaw: 'Factura electrónica 001-002-000045678',
    parsedProviderName: 'Distribuidora XYZ',
    parsedProviderRuc: '0999999999001',
    parsedAmount: 125.5,
    parsedDate: '2026-08-08',
    parsedCategory: 'Insumos',
    confidence: 0.92,
    status: 'pendiente',
  },
  {
    id: 'draft-002',
    receivedAt: '2026-08-07T19:40:00.000Z',
    fromAddress: 'notificaciones@empaquesecuador.com',
    subjectRaw: 'Su comprobante de compra #88213',
    parsedProviderName: 'Empaques Ecuador Cía. Ltda.',
    parsedProviderRuc: '1792233445001',
    parsedAmount: 48.9,
    parsedDate: '2026-08-07',
    parsedCategory: 'Empaques',
    confidence: 0.87,
    status: 'pendiente',
  },
];
