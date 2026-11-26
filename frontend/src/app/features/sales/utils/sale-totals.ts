/**
 * Vista previa de los totales de una venta, con el mismo redondeo que el backend
 * (app/sri/totales.py): base de cada línea redondeada a centavos y, luego, el IVA de
 * cada tarifa sobre la suma de sus bases. El backend recalcula todo al registrar.
 */

/** Código de porcentaje del SRI → tarifa en %. */
export const VAT_RATES: Record<string, number> = {
  '0': 0,
  '4': 15,
  '5': 5,
  '6': 0, // no objeto de IVA
  '7': 0, // exento
};

/** Sin código (productos antiguos), se asume la tarifa general. */
export const DEFAULT_VAT_CODE = '4';

export interface TotalsLine {
  unitPrice: number;
  quantity: number;
  vatPercentageCode?: string | null;
}

export interface RateTotal {
  rate: number;
  base: number;
  iva: number;
}

export interface SaleTotals {
  subtotal: number;
  iva: number;
  total: number;
  /** Una fila por tarifa usada, de mayor a menor. */
  byRate: RateTotal[];
}

/** Redondeo comercial a centavos (ROUND_HALF_UP para montos positivos). */
export function roundCents(value: number): number {
  return Math.round((value + Number.EPSILON) * 100) / 100;
}

export function rateFor(code: string | null | undefined): number {
  return VAT_RATES[code ?? DEFAULT_VAT_CODE] ?? VAT_RATES[DEFAULT_VAT_CODE];
}

export function calculateSaleTotals(lines: TotalsLine[]): SaleTotals {
  const bases = new Map<number, number>();
  let subtotal = 0;
  for (const line of lines) {
    const base = roundCents(line.unitPrice * line.quantity);
    const rate = rateFor(line.vatPercentageCode);
    bases.set(rate, roundCents((bases.get(rate) ?? 0) + base));
    subtotal = roundCents(subtotal + base);
  }

  const byRate = [...bases.entries()]
    .sort(([a], [b]) => b - a)
    .map(([rate, base]) => ({ rate, base, iva: roundCents((base * rate) / 100) }));
  const iva = roundCents(byRate.reduce((sum, r) => sum + r.iva, 0));
  return { subtotal, iva, total: roundCents(subtotal + iva), byRate };
}
