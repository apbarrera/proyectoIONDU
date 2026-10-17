import { Expense } from '../features/expenses/models/expense.model';
import { daysAgo, round2, seededRandom } from './seed-dates.util';

const SUPPLIERS = [
  { name: 'Molinos del Valle S.A.', ruc: '1790012345001', category: 'Insumos', base: 38, iva: true },
  { name: 'Distribuidora El Cacao', ruc: '1791234567001', category: 'Insumos', base: 54, iva: true },
  { name: 'Empaques Andinos', ruc: '1792345678001', category: 'Empaque', base: 22, iva: true },
  { name: 'Transportes Ruiz', ruc: '1793456789001', category: 'Transporte', base: 15, iva: false },
  { name: 'CNEL Empresa Eléctrica', ruc: '1790654321001', category: 'Servicios', base: 62, iva: false },
] as const;

const HISTORY_DAYS = 44;

/** Gastos de las últimas semanas, repartidos entre proveedores y categorías. */
function buildExpenses(): Expense[] {
  const random = seededRandom(20260818);
  const expenses: Expense[] = [];
  let index = 1;

  for (let day = HISTORY_DAYS; day >= 0; day -= 2 + Math.floor(random() * 3)) {
    const supplier = SUPPLIERS[Math.floor(random() * SUPPLIERS.length)];
    const amount = round2(supplier.base * (0.7 + random() * 0.8));
    const ivaAmount = supplier.iva ? round2(amount * 0.15) : 0;
    expenses.push({
      id: `exp-g-${index++}`,
      date: daysAgo(day, 10 + Math.floor(random() * 6)),
      category: supplier.category,
      providerName: supplier.name,
      providerRuc: supplier.ruc,
      amount,
      ivaAmount,
      total: round2(amount + ivaAmount),
      paymentMethod: 'transferencia',
      description: `Compra a ${supplier.name}`,
      sourceType: 'manual',
      createdBy: 'María Fernanda Salazar',
    });
  }
  return expenses;
}

export const EXPENSES_HISTORY_MOCK: Expense[] = buildExpenses();
