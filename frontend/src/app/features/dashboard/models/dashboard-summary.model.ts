export interface TopProduct {
  productId: string;
  name: string;
  unitsSold: number;
  /** Subtotal sin IVA de las líneas vendidas. */
  revenue: number;
}

export interface DailyPoint {
  date: string;
  income: number;
  expenses: number;
}

export interface ExpenseByCategory {
  categoryId: number;
  name: string;
  total: number;
}

export interface LowStockProduct {
  productId: string;
  name: string;
  unit: string;
  currentStock: number;
  minStock: number;
}

/** Estado actual del inventario (no depende del período). */
export interface InventorySummary {
  activeProducts: number;
  lowStockCount: number;
  inventoryValue: number;
  lowStockProducts: LowStockProduct[];
}

export interface DashboardSummary {
  income: number;
  expenses: number;
  profit: number;
  salesCount: number;
  expensesCount: number;
  averageTicket: number;
  topProducts: TopProduct[];
  dailySeries: DailyPoint[];
  expensesByCategory: ExpenseByCategory[];
  inventory: InventorySummary;
}

export const EMPTY_DASHBOARD_SUMMARY: DashboardSummary = {
  income: 0,
  expenses: 0,
  profit: 0,
  salesCount: 0,
  expensesCount: 0,
  averageTicket: 0,
  topProducts: [],
  dailySeries: [],
  expensesByCategory: [],
  inventory: { activeProducts: 0, lowStockCount: 0, inventoryValue: 0, lowStockProducts: [] },
};
