import { Invoice } from '../features/billing/models/invoice.model';

export const INVOICES_MOCK: Invoice[] = [
  {
    id: 'inv-001',
    numero: '001-001-000000098',
    claveAcceso: '0708202601179234567800120010010000000981234567816',
    customer: { rucOrCedula: '9999999999', razonSocial: 'Consumidor Final', email: '' },
    items: [
      { productId: 'prod-torta-chocolate', productName: 'Torta de Chocolate', quantity: 2, unitPrice: 25, subtotal: 50 },
    ],
    subtotal: 50,
    iva: 7.5,
    total: 57.5,
    status: 'autorizada',
    statusHistory: [
      { status: 'borrador', timestamp: '2026-08-07T15:40:00.000Z' },
      { status: 'procesando', timestamp: '2026-08-07T15:40:02.000Z' },
      { status: 'pendiente', timestamp: '2026-08-07T15:40:04.000Z' },
      { status: 'autorizada', timestamp: '2026-08-07T15:40:07.000Z' },
    ],
    createdAt: '2026-08-07T15:40:00.000Z',
    authorizedAt: '2026-08-07T15:40:07.000Z',
    createdBy: 'Juan Carlos Pérez',
  },
];
