import { Expense } from '../features/expenses/models/expense.model';
import { daysAgo } from './seed-dates.util';
import { EXPENSES_HISTORY_MOCK } from './expenses-history.mock';

const BASE_EXPENSES: Expense[] = [
  {
    id: 'exp-001',
    date: daysAgo(4, 10),
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
    date: daysAgo(3, 16),
    category: 'Servicios',
    providerName: 'CNEL Empresa Eléctrica',
    providerRuc: '1790654321001',
    amount: 64.2,
    ivaAmount: 0,
    total: 64.2,
    paymentMethod: 'transferencia',
    description: 'Planilla eléctrica del local',
    sourceType: 'manual',
    createdBy: 'María Fernanda Salazar',
  },
];

export const EXPENSES_MOCK: Expense[] = [...BASE_EXPENSES, ...EXPENSES_HISTORY_MOCK];
