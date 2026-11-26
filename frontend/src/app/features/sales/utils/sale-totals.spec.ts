import { calculateSaleTotals, rateFor, roundCents } from './sale-totals';

describe('calculateSaleTotals', () => {
  it('usa la tarifa de cada producto, no un 15 % fijo', () => {
    const totals = calculateSaleTotals([
      { unitPrice: 0.75, quantity: 1, vatPercentageCode: '4' }, // agua: 15 %
      { unitPrice: 2.0, quantity: 2, vatPercentageCode: '0' }, // pan: 0 %
    ]);

    expect(totals.subtotal).toBe(4.75);
    expect(totals.iva).toBe(0.11); // solo sobre los 0,75 del agua
    expect(totals.total).toBe(4.86);
    expect(totals.byRate).toEqual([
      { rate: 15, base: 0.75, iva: 0.11 },
      { rate: 0, base: 4, iva: 0 },
    ]);
  });

  it('redondea el IVA por tarifa sobre la suma de bases, como el backend', () => {
    // Por línea serían 0,15 + 0,15 = 0,30; sobre la suma (2,00 × 15 %) también 0,30.
    // Con 0,33 + 0,33 = 0,66 → 0,099 → 0,10 (y no 0,05 + 0,05).
    const totals = calculateSaleTotals([
      { unitPrice: 0.33, quantity: 1, vatPercentageCode: '4' },
      { unitPrice: 0.33, quantity: 1, vatPercentageCode: '4' },
    ]);
    expect(totals.iva).toBe(0.1);
    expect(totals.total).toBe(0.76);
  });

  it('separa el IVA del 5 % y suma las tarifas', () => {
    const totals = calculateSaleTotals([
      { unitPrice: 10, quantity: 1, vatPercentageCode: '4' },
      { unitPrice: 10, quantity: 1, vatPercentageCode: '5' },
    ]);
    expect(totals.byRate.map((r) => [r.rate, r.iva])).toEqual([
      [15, 1.5],
      [5, 0.5],
    ]);
    expect(totals.total).toBe(22);
  });

  it('sin código asume la tarifa general y un carrito vacío da cero', () => {
    expect(rateFor(undefined)).toBe(15);
    expect(rateFor('99')).toBe(15);
    expect(calculateSaleTotals([])).toEqual({ subtotal: 0, iva: 0, total: 0, byRate: [] });
  });

  it('redondea medio centavo hacia arriba', () => {
    expect(roundCents(1.005)).toBe(1.01);
    expect(roundCents(0.125)).toBe(0.13);
  });
});
