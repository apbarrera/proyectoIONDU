export interface StockAdjustment {
  id: string;
  productId: string;
  productName: string;
  previousStock: number;
  newStock: number;
  quantityDelta: number;
  reason: string;
  date: string;
  createdBy: string;
}

export interface ProductionRun {
  id: string;
  recipeId: string;
  productId: string;
  productName: string;
  unitsProduced: number;
  estimatedCost: number;
  date: string;
  producedBy: string;
}
