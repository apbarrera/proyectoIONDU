import { Sale, SaleLineItem } from '../features/sales/models/sale.model';
import { PRODUCT_IDS } from './seed-ids.const';
import { daysAgo, round2, seededRandom } from './seed-dates.util';

const CATALOG = [
  { productId: PRODUCT_IDS.TORTA_CHOCOLATE, productName: 'Torta de Chocolate', unitPrice: 25, qty: [1, 3] },
  { productId: PRODUCT_IDS.BROWNIE, productName: 'Brownie de Chocolate', unitPrice: 3.5, qty: [2, 8] },
  { productId: PRODUCT_IDS.CAFE_MOLIDO, productName: 'Café Molido Premium 250g', unitPrice: 6.5, qty: [1, 4] },
] as const;

const CUSTOMERS = ['Consumidor Final', 'Cafetería Buen Día', 'Panadería La Espiga', 'Eventos Martínez', 'Consumidor Final'];
const PAYMENTS = ['efectivo', 'tarjeta', 'transferencia'] as const;
const CASHIERS = ['Juan Carlos Pérez', 'María Fernanda Salazar'];

const HISTORY_DAYS = 45;
const FIRST_FOLIO = 125;

/** Ventas de las últimas semanas para que el dashboard y los historiales tengan datos reales de ejemplo. */
function buildSales(): Sale[] {
  const random = seededRandom(20260817);
  const sales: Sale[] = [];
  let folio = FIRST_FOLIO;

  for (let day = HISTORY_DAYS; day >= 0; day--) {
    if (random() < 0.15) continue;
    const salesToday = 1 + Math.floor(random() * 3);

    for (let n = 0; n < salesToday; n++) {
      const lines = 1 + Math.floor(random() * 2);
      const items: SaleLineItem[] = [];
      for (let l = 0; l < lines; l++) {
        const product = CATALOG[Math.floor(random() * CATALOG.length)];
        if (items.some((item) => item.productId === product.productId)) continue;
        const quantity = product.qty[0] + Math.floor(random() * (product.qty[1] - product.qty[0] + 1));
        items.push({
          productId: product.productId,
          productName: product.productName,
          quantity,
          unitPrice: product.unitPrice,
          subtotal: round2(quantity * product.unitPrice),
        });
      }

      const subtotal = round2(items.reduce((sum, item) => sum + item.subtotal, 0));
      const ivaAmount = round2(subtotal * 0.15);
      sales.push({
        id: `sale-g-${folio}`,
        folio: String(folio).padStart(6, '0'),
        date: daysAgo(day, 9 + Math.floor(random() * 9)),
        customerName: CUSTOMERS[Math.floor(random() * CUSTOMERS.length)],
        items,
        subtotal,
        ivaAmount,
        total: round2(subtotal + ivaAmount),
        paymentMethod: PAYMENTS[Math.floor(random() * PAYMENTS.length)],
        status: 'completada',
        createdBy: CASHIERS[Math.floor(random() * CASHIERS.length)],
      });
      folio++;
    }
  }
  return sales;
}

export const SALES_HISTORY_MOCK: Sale[] = buildSales();
