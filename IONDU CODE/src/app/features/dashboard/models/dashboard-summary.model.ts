export interface TopProduct {
  productId: string;
  name: string;
  unitsSold: number;
  revenue: number;
}

export interface DailyPoint {
  date: string;
  income: number;
}

export interface DashboardSummary {
  income: number;
  expenses: number;
  profit: number;
  salesCount: number;
  averageTicket: number;
  topProducts: TopProduct[];
  dailySeries: DailyPoint[];
}
