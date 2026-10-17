/** Fecha ISO de hace `days` días a la hora indicada: los datos de ejemplo siempre caen en el período actual. */
export function daysAgo(days: number, hour = 12): string {
  const date = new Date();
  date.setDate(date.getDate() - days);
  date.setHours(hour, 0, 0, 0);
  return date.toISOString();
}

/** Generador pseudoaleatorio determinístico (LCG): mismos datos de ejemplo en cada carga. */
export function seededRandom(seed: number): () => number {
  let state = seed % 2147483647;
  return () => {
    state = (state * 16807) % 2147483647;
    return (state - 1) / 2147483646;
  };
}

export const round2 = (value: number): number => Math.round(value * 100) / 100;
