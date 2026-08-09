export type PeriodOption = 'hoy' | '7dias' | 'esteMes' | 'mesAnterior' | 'personalizado';

export interface DateRange {
  option: PeriodOption;
  from: string;
  to: string;
}

function toIsoDate(date: Date): string {
  return date.toISOString().slice(0, 10);
}

export function resolveDateRange(option: PeriodOption, custom?: { from: string; to: string }): DateRange {
  const now = new Date();
  const startOfDay = (d: Date) => new Date(d.getFullYear(), d.getMonth(), d.getDate());

  switch (option) {
    case 'hoy': {
      const today = startOfDay(now);
      return { option, from: toIsoDate(today), to: toIsoDate(today) };
    }
    case '7dias': {
      const from = startOfDay(now);
      from.setDate(from.getDate() - 6);
      return { option, from: toIsoDate(from), to: toIsoDate(now) };
    }
    case 'esteMes': {
      const from = new Date(now.getFullYear(), now.getMonth(), 1);
      return { option, from: toIsoDate(from), to: toIsoDate(now) };
    }
    case 'mesAnterior': {
      const from = new Date(now.getFullYear(), now.getMonth() - 1, 1);
      const to = new Date(now.getFullYear(), now.getMonth(), 0);
      return { option, from: toIsoDate(from), to: toIsoDate(to) };
    }
    case 'personalizado':
      return { option, from: custom?.from ?? toIsoDate(now), to: custom?.to ?? toIsoDate(now) };
  }
}

export const PERIOD_OPTION_LABELS: Record<PeriodOption, string> = {
  hoy: 'Hoy',
  '7dias': 'Últimos 7 días',
  esteMes: 'Este mes',
  mesAnterior: 'Mes anterior',
  personalizado: 'Personalizado',
};
