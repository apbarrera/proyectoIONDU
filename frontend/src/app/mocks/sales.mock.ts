import { Sale } from '../features/sales/models/sale.model';
import { PRODUCT_IDS } from './seed-ids.const';

export const SALES_MOCK: Sale[] = [
  {
    id: 'sale-001',
    folio: '000123',
    date: '2026-08-07T15:40:00.000Z',
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
    date: '2026-08-08T10:15:00.000Z',
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
