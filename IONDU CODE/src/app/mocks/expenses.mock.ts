import { Expense } from '../features/expenses/models/expense.model';

export const EXPENSES_MOCK: Expense[] = [
  {
    id: 'exp-001',
    date: '2026-08-05T10:00:00.000Z',
    category: 'Insumos',
    providerName: 'Molinos del Valle S.A.',
    providerRuc: '1790012345001',
    amount: 27.5,
    ivaAmount: 4.13,
    total: 31.63,
    paymentMethod: 'transferencia',
    description: 'Compra de 25kg de harina de trigo',
    sourceType: 'manual',
    createdBy: 'María Fernanda Salazar',
  },
  {
    id: 'exp-002',
    date: '2026-08-06T16:20:00.000Z',
    category: 'Servicios',
    providerName: 'CNEL Empresa Eléctrica',
    providerRuc: '1790654321001',
    amount: 64.2,
    ivaAmount: 0,
    total: 64.2,
    paymentMethod: 'transferencia',
    description: 'Planilla eléctrica del local, agosto 2026',
    sourceType: 'manual',
    createdBy: 'María Fernanda Salazar',
  },
];
