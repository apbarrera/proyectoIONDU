import { Sale } from '../features/sales/models/sale.model';
import { PRODUCT_IDS } from './seed-ids.const';
import { daysAgo } from './seed-dates.util';
import { SALES_HISTORY_MOCK } from './sales-history.mock';

const BASE_SALES: Sale[] = [
  {
    id: 'sale-001',
    folio: '000123',
    date: daysAgo(3, 15),
    customerName: 'Consumidor Final',
    items: [
      {
        productId: PRODUCT_IDS.TORTA_CHOCOLATE,
        productName: 'Torta de Chocolate',
        quantity: 2,
        unitPrice: 25,
        subtotal: 50,
      },
    ],
    subtotal: 50,
    ivaAmount: 7.5,
    total: 57.5,
    paymentMethod: 'tarjeta',
    status: 'completada',
    createdBy: 'Juan Carlos Pérez',
  },
  {
    id: 'sale-002',
    folio: '000124',
    date: daysAgo(2, 10),
    customerName: 'Cafetería Buen Día',
    items: [
      {
        productId: PRODUCT_IDS.BROWNIE,
        productName: 'Brownie de Chocolate',
        quantity: 6,
        unitPrice: 3.5,
        subtotal: 21,
      },
      {
        productId: PRODUCT_IDS.CAFE_MOLIDO,
        productName: 'Café Molido Premium 250g',
        quantity: 2,
        unitPrice: 6.5,
        subtotal: 13,
      },
    ],
    subtotal: 34,
    ivaAmount: 5.1,
    total: 39.1,
    paymentMethod: 'efectivo',
    status: 'completada',
    createdBy: 'Juan Carlos Pérez',
  },
];

const FIRST_FOLIO = 101;

/** Cronológicas, con folios consecutivos (el más antiguo primero) y listadas de la más reciente a la más antigua. */
export const SALES_MOCK: Sale[] = [...BASE_SALES, ...SALES_HISTORY_MOCK]
  .sort((a, b) => a.date.localeCompare(b.date))
  .map((sale, index) => ({ ...sale, folio: String(FIRST_FOLIO + index).padStart(6, '0') }))
  .reverse();
